import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-01-bfb40d59d7ff"
LOCATION = "us-central1"  # serverless mode requires us-central1
GCS_PATH = "gs://moneysprout-media-qwiklabs-gcp-01-bfb40d59d7ff/rag/moneysprout_guardrails_and_guidelines.txt"

PARSING_PROMPT = (
    "Extract all financial discipline rules, Needs vs Wants guidelines, digital piggy bank bookkeeping, "
    "etiquette practices, child privacy guardrails, and educational principles. Output clean, self-contained prose."
)

def main():
    print(f"Initializing Vertex AI RAG in project {PROJECT_ID} ({LOCATION})...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Set serverless mode for the project/location
    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )
    print("Serverless RAG Engine config set successfully.")

    # 2. Create Serverless RAG Corpus
    corpus = rag.create_corpus(
        display_name="moneysprout-kids-guardrails-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    print("Created RAG Corpus!")
    print("CORPUS_NAME:", corpus.name)

    # 3. Import, chunk, and embed document
    print(f"Importing {GCS_PATH} into corpus...")
    resp = rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"Successfully imported {resp.imported_rag_files_count} file(s) into corpus!")
    print(f"Saved Corpus Resource Name: {corpus.name}")

if __name__ == "__main__":
    main()
