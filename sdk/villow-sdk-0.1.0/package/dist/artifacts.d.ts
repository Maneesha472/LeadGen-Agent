export type ArtifactType = 'file_set' | 'structured_fields' | 'message_draft' | 'event_proposal' | 'table_data' | 'generic';
export type ArtifactPayload = Record<string, unknown>;
export interface VillowArtifact {
    artifact_type: ArtifactType;
    title: string;
    type_payload: ArtifactPayload;
    preview_data: ArtifactPayload;
    destination_proposal?: ArtifactPayload;
    metadata?: ArtifactPayload;
}
export declare class Artifact {
    static fileSet(input: {
        files: ArtifactPayload[];
        previewUrls?: string[];
        destinationProposal?: ArtifactPayload;
        title?: string;
        metadata?: ArtifactPayload;
    }): VillowArtifact;
    static structuredFields(input: {
        fields: ArtifactPayload;
        title?: string;
        confidence?: Record<string, number>;
    }): VillowArtifact;
    static messageDraft(input: {
        subject: string;
        body: string;
        to?: string[];
        cc?: string[];
        bcc?: string[];
        title?: string;
    }): VillowArtifact;
    static eventProposal(input: {
        title: string;
        start: string;
        end: string;
        attendees?: string[];
        location?: string;
    }): VillowArtifact;
    static tableData(input: {
        columns: string[];
        rows: unknown[][];
        title?: string;
    }): VillowArtifact;
    static generic(input: {
        payload: ArtifactPayload;
        title?: string;
        previewData?: ArtifactPayload;
    }): VillowArtifact;
}
