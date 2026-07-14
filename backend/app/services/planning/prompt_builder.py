from app.services.knowledge_service import knowledge_service
from app.services.project_service import project_service

class PromptBuilder:
    """
    Assembles contextual prompts for the AI Planning Engine.
    Minimizes token usage by selectively injecting only the required context.
    """

    @staticmethod
    def build_project_context(project_id: str) -> str:
        """Builds a summary of the project and its knowledge base."""
        project = project_service.get_project(project_id)
        if not project:
            return "Project context not found."

        docs = knowledge_service.list_documents(project_id)
        
        context = [
            f"Project Name: {project.name}",
            f"Project Description: {project.description}",
            f"Primary URL: {project.primary_url or 'N/A'}",
            "\n--- Project Knowledge base ---"
        ]

        if not docs:
            context.append("No uploaded knowledge documents found.")
        else:
            for doc in docs:
                context.append(f"\nDocument Title: {doc.title} ({doc.document_type.value})")
                context.append(f"Description: {doc.description}")
                # We would theoretically read the physical file here, but for now we'll rely on metadata/descriptions
                # Or we can read text files if they exist. For PDF/DOCX, a real system would extract text.
                # Since QAForge is a prototype, we'll extract text if it's a markdown or txt file.
                try:
                    if doc.file_path.endswith('.txt') or doc.file_path.endswith('.md'):
                        with open(doc.file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            context.append(f"Content:\n{content}")
                except Exception as e:
                    context.append(f"(Could not read file content: {e})")

        return "\n".join(context)
