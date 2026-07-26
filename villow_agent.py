import os
import sys
import time
import asyncio
from typing import Any, Dict

from villow import Agent, Artifact, task_template, events_to_stream

# Ensure the backend module is accessible
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.database import SessionLocal, User, Execution, Company, Contact, init_db
from backend.scraper import LeadGenerator, LOGS_DIR

init_db()

class VillowLeadGenerationAgent(Agent):
    @task_template("lead_generation")
    async def prepare(self, inputs: Dict[str, Any], ctx: Any):
        return {"state": "ready_to_authorize"}

    @task_template("lead_generation")
    async def run(self, inputs: Dict[str, Any], ctx: Any):
        category = inputs.get("category", "")
        location = inputs.get("location", "")
        keywords = inputs.get("keywords", "")
        max_results = inputs.get("max_results", 50)

        db = SessionLocal()
        try:
            # Create a dummy user for the Villow agent execution if not exists
            user = db.query(User).filter(User.email == "villow_agent@system.local").first()
            if not user:
                user = User(email="villow_agent@system.local", hashed_password="N/A", max_search_results=max_results)
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                user.max_search_results = max_results
                db.commit()
                db.refresh(user)

            # Create an execution record
            execution = Execution(
                user_id=user.id,
                category=category,
                location=location,
                keywords=keywords,
                status="Running"
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            
            log_file_path = os.path.join(LOGS_DIR, f"run_{execution.id}.log")
            
            # Start the synchronous scraper in a background thread
            generator = LeadGenerator(db, execution.id)
            
            scraper_task = asyncio.create_task(asyncio.to_thread(generator.run))
            
            # Read logs and stream them to Villow
            last_pos = 0
            while not scraper_task.done():
                if os.path.exists(log_file_path):
                    with open(log_file_path, "r", encoding="utf-8") as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()
                        
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                await ctx.report_progress({
                                    "event_type": "milestone",
                                    "milestone": {"label": line}
                                })
                await asyncio.sleep(0.5)
                
            # Wait for the thread to fully finish
            await scraper_task
            
            # Flush remaining logs
            if os.path.exists(log_file_path):
                with open(log_file_path, "r", encoding="utf-8") as f:
                    f.seek(last_pos)
                    for line in f.readlines():
                        line = line.strip()
                        if line:
                            await ctx.report_progress({
                                "event_type": "milestone",
                                "milestone": {"label": line}
                            })

            # Fetch results from DB
            db.refresh(execution)
            contacts = db.query(Contact).join(Company).filter(Company.execution_id == execution.id).all()
            
            # Format results for Villow Artifact
            rows = []
            for c in contacts:
                comp = db.query(Company).filter(Company.id == c.company_id).first()
                rows.append([
                    c.name or "",
                    c.designation or "",
                    c.email or "",
                    c.phone or "",
                    c.linkedin_url or "",
                    comp.name if comp else "",
                    comp.website if comp else "",
                    comp.industry if comp else "",
                    c.status or ""
                ])
                
            columns = ["Name", "Designation", "Email", "Phone", "LinkedIn", "Company", "Website", "Industry", "Status"]
            
            await ctx.stage_artifact(
                Artifact.table_data(
                    title=f"Leads for {category} in {location}",
                    columns=columns,
                    rows=rows
                )
            )

        finally:
            db.close()
            
        return events_to_stream(ctx.emitted_events)

# For running locally via uvicorn villow_agent:app
from villow.server import create_app

agent = VillowLeadGenerationAgent(
    publisher_id="PUBLISHER_PLACEHOLDER",
    agent_id="AGENT_PLACEHOLDER",
    key_id="KEY_PLACEHOLDER",
    secret="SECRET_PLACEHOLDER",
)

app = create_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
