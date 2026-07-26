export class Artifact {
    static fileSet(input) {
        return artifact('file_set', {
            title: input.title ?? 'Files',
            typePayload: { files: input.files },
            previewData: { preview_urls: input.previewUrls ?? [], file_count: input.files.length },
            destinationProposal: input.destinationProposal,
            metadata: input.metadata,
        });
    }
    static structuredFields(input) {
        return artifact('structured_fields', {
            title: input.title ?? 'Structured fields',
            typePayload: { fields: input.fields, confidence: input.confidence ?? {} },
            previewData: { field_count: Object.keys(input.fields).length },
        });
    }
    static messageDraft(input) {
        return artifact('message_draft', {
            title: input.title ?? 'Message draft',
            typePayload: {
                to: input.to ?? [],
                cc: input.cc ?? [],
                bcc: input.bcc ?? [],
                subject: input.subject,
                body: input.body,
            },
            previewData: { subject: input.subject, body_preview: input.body.slice(0, 200) },
        });
    }
    static eventProposal(input) {
        return artifact('event_proposal', {
            title: input.title,
            typePayload: {
                title: input.title,
                start: input.start,
                end: input.end,
                attendees: input.attendees ?? [],
                location: input.location,
            },
            previewData: { start: input.start, end: input.end },
        });
    }
    static tableData(input) {
        return artifact('table_data', {
            title: input.title ?? 'Table data',
            typePayload: { columns: input.columns, rows: input.rows },
            previewData: { column_count: input.columns.length, row_count: input.rows.length, sample_rows: input.rows.slice(0, 5) },
        });
    }
    static generic(input) {
        return artifact('generic', {
            title: input.title ?? 'Artifact',
            typePayload: input.payload,
            previewData: input.previewData ?? {},
        });
    }
}
function artifact(artifactType, input) {
    const payload = {
        artifact_type: artifactType,
        title: input.title,
        type_payload: input.typePayload,
        preview_data: input.previewData,
    };
    if (input.destinationProposal)
        payload.destination_proposal = input.destinationProposal;
    if (input.metadata)
        payload.metadata = input.metadata;
    return payload;
}
