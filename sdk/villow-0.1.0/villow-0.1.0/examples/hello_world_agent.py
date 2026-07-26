from __future__ import annotations

from villow import Agent, Artifact, Composition, Question, preview, task_template


class HelloWorldAgent(Agent):
    @task_template("hello_world")
    def prepare(self, inputs, ctx):
        composition = Composition.input(
            [
                Composition.dropdown_with_descriptions(
                    "tone",
                    label="Tone",
                    options=[{"id": "friendly", "label": "Friendly"}, {"id": "formal", "label": "Formal"}],
                    default="friendly",
                )
            ],
            task_template="hello_world",
            composition_id="hello_world.v1",
        )
        if not ctx.has_answer("tone"):
            return ctx.request_clarification(
                [
                    Question.single_select(
                        id="tone",
                        label="Tone",
                        options=["friendly", "formal"],
                        default="friendly",
                        decide_for_me={"value": "friendly"},
                    )
                ],
                composition_response=composition,
            )
        normalized = {"name": inputs.get("name", "there"), "tone": ctx.answer("tone")}
        return ctx.ready_to_authorize(normalized_inputs=normalized, composition_response=composition)

    @preview("hello_world")
    def preview_hello(self, inputs, ctx):
        return {"type": "text", "value": f"Hello {inputs.get('name', 'there')}"}

    @task_template("hello_world")
    async def run(self, inputs, ctx):
        await ctx.stage_artifact(Artifact.generic(payload={"message": f"Hello {inputs['name']}", "tone": inputs["tone"]}))
