"""AI Horizon CLI - Main entry point."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.config import get_settings
from src.classification.models import Artifact, SourceType

# Initialize
app = typer.Typer(
    name="horizon",
    help="AI Horizon - Cybersecurity Workforce Impact Analysis",
    add_completion=False,
)
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_source_type(file_path: Path) -> SourceType:
    """Determine source type from file extension."""
    ext = file_path.suffix.lower()
    mapping = {
        ".pdf": SourceType.PDF,
        ".docx": SourceType.DOCX,
        ".doc": SourceType.DOCX,
        ".txt": SourceType.TEXT,
        ".md": SourceType.TEXT,
    }
    return mapping.get(ext, SourceType.UNKNOWN)


@app.command()
def classify(
    file: Path = typer.Argument(..., help="Path to the file to classify"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Artifact title"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Source URL"),
    store: bool = typer.Option(True, "--store/--no-store", help="Store after classification"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Classify a document and optionally store it."""
    from src.classification.classifier import HorizonClassifier
    from src.extraction.router import extract_content
    from src.storage.file_search import HorizonStorage
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    console.print(f"\n[bold blue]📄 Processing:[/] {file.name}")
    
    # Extract content
    with console.status("Extracting content..."):
        content = extract_content(file)
    
    console.print(f"[green]✓[/] Extracted {len(content):,} characters")
    
    # Create artifact
    artifact = Artifact(
        artifact_id=f"artifact_{uuid.uuid4().hex[:12]}",
        title=title or file.stem,
        content=content,
        source_url=url,
        source_type=get_source_type(file),
        filename=file.name,
        retrieved_on=datetime.now(),
    )
    
    # Classify
    with console.status("Classifying with Gemini..."):
        classifier = HorizonClassifier()
        result = classifier.classify(artifact)
        artifact.apply_classification(result)
    
    # Display results
    _display_classification_result(artifact, result)
    
    # Store if requested
    if store:
        settings = get_settings()
        if settings.artifacts_store_name:
            with console.status("Storing artifact..."):
                storage = HorizonStorage()
                doc_id = storage.store_artifact(artifact)
            console.print(f"[green]✓[/] Stored as: {doc_id}")
        else:
            console.print("[yellow]⚠[/] Artifacts store not configured. Run 'horizon setup' first.")


def _display_classification_result(artifact: Artifact, result):
    """Display classification results in a nice format."""
    # Classification panel
    classification_color = {
        "Replace": "red",
        "Augment": "yellow", 
        "Remain Human": "green",
        "New Task": "blue",
    }.get(result.classification.value, "white")
    
    console.print(Panel(
        f"[bold {classification_color}]{result.classification.value}[/] "
        f"(Confidence: {result.confidence:.0%})",
        title="Classification",
    ))
    
    # Rationale
    console.print(f"\n[bold]Rationale:[/] {result.rationale}")
    
    # Scores table
    scores_table = Table(title="Scores", show_header=True)
    scores_table.add_column("Metric", style="cyan")
    scores_table.add_column("Score", justify="right")
    scores_table.add_row("Credibility", f"{result.scores.credibility:.0%}")
    scores_table.add_row("Impact", f"{result.scores.impact:.0%}")
    scores_table.add_row("Specificity", f"{result.scores.specificity:.0%}")
    console.print(scores_table)
    
    # DCWF Tasks
    if result.dcwf_tasks:
        tasks_table = Table(title="DCWF Task Mappings", show_header=True)
        tasks_table.add_column("Task ID", style="cyan")
        tasks_table.add_column("Relevance", justify="right")
        tasks_table.add_column("Impact", width=50)
        
        for task in result.dcwf_tasks[:5]:  # Show top 5
            tasks_table.add_row(
                task.task_id,
                f"{task.relevance_score:.0%}",
                task.impact_description[:50] + "..." if len(task.impact_description) > 50 else task.impact_description,
            )
        console.print(tasks_table)
    
    # Key Findings
    if result.key_findings:
        console.print("\n[bold]Key Findings:[/]")
        for finding in result.key_findings:
            console.print(f"  • {finding}")


@app.command()
def chat():
    """Start interactive chat with the AI Horizon knowledge base."""
    from src.agents.chat_agent import HorizonChatAgent
    
    console.print(Panel(
        "[bold]AI Horizon Research Assistant[/]\n\n"
        "Ask questions about:\n"
        "• DCWF tasks and work roles\n"
        "• Classified artifacts\n"
        "• AI impact on cybersecurity workforce\n\n"
        "Type 'exit' or 'quit' to end the session.",
        title="Welcome",
    ))
    
    agent = HorizonChatAgent()
    
    while True:
        try:
            query = Prompt.ask("\n[bold blue]You[/]")
            
            if query.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye![/]")
                break
            
            if not query.strip():
                continue
            
            with console.status("Thinking..."):
                response = agent.chat(query)
            
            console.print(f"\n[bold green]Assistant:[/] {response}")
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/]")
            break


@app.command()
def setup():
    """Set up File Search stores for AI Horizon."""
    from src.storage.file_search import FileSearchStore
    
    console.print("[bold]Setting up AI Horizon File Search stores...[/]\n")
    
    store = FileSearchStore()
    
    # Create DCWF store
    with console.status("Creating DCWF reference store..."):
        dcwf_name = store.create_store("ai-horizon-dcwf")
    console.print(f"[green]✓[/] DCWF Store: {dcwf_name}")
    
    # Create artifacts store
    with console.status("Creating artifacts store..."):
        artifacts_name = store.create_store("ai-horizon-artifacts")
    console.print(f"[green]✓[/] Artifacts Store: {artifacts_name}")
    
    # Instructions
    console.print(Panel(
        f"Add these to your .env file:\n\n"
        f"DCWF_STORE_NAME={dcwf_name}\n"
        f"ARTIFACTS_STORE_NAME={artifacts_name}",
        title="Next Steps",
    ))


@app.command()
def import_dcwf(
    file: Path = typer.Argument(..., help="Path to DCWF JSON file"),
):
    """Import DCWF tasks into the reference store."""
    import json
    from src.classification.models import DCWFTask
    from src.storage.file_search import FileSearchStore
    
    settings = get_settings()
    
    if not settings.dcwf_store_name:
        console.print("[red]Error:[/] DCWF store not configured. Run 'horizon setup' first.")
        raise typer.Exit(1)
    
    console.print(f"[bold]Importing DCWF tasks from:[/] {file}")
    
    # Load tasks
    with open(file) as f:
        data = json.load(f)
    
    # Parse tasks
    tasks = []
    for item in data:
        tasks.append(DCWFTask(
            task_id=item.get("task_id", item.get("Task ID", "")),
            nist_sp_id=item.get("nist_sp_id", item.get("NIST SP ID")),
            task_name=item.get("task_name", item.get("Task Name", "")),
            task_description=item.get("task_description", item.get("Task Description", "")),
            work_role=item.get("work_role", item.get("Work Role")),
            work_role_id=item.get("work_role_id", item.get("Work Role ID")),
            competency_area=item.get("competency_area", item.get("Competency Area")),
        ))
    
    console.print(f"[green]✓[/] Loaded {len(tasks)} tasks")
    
    # Upload
    store = FileSearchStore()
    with console.status("Uploading to File Search..."):
        doc_names = store.upload_dcwf_tasks(settings.dcwf_store_name, tasks)
    
    console.print(f"[green]✓[/] Uploaded {len(doc_names)} batch files")


@app.command()
def status():
    """Show current configuration status."""
    settings = get_settings()
    
    table = Table(title="AI Horizon Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Status")
    
    # API Key
    api_key_status = "✓" if settings.gemini_api_key else "✗"
    api_key_display = settings.gemini_api_key[:10] + "..." if settings.gemini_api_key else "Not set"
    table.add_row("Gemini API Key", api_key_display, f"[green]{api_key_status}[/]" if api_key_status == "✓" else f"[red]{api_key_status}[/]")
    
    # Model
    table.add_row("Model", settings.gemini_model, "[green]✓[/]")
    
    # Stores
    dcwf_status = "✓" if settings.dcwf_store_name else "✗"
    table.add_row("DCWF Store", settings.dcwf_store_name or "Not set", f"[green]{dcwf_status}[/]" if dcwf_status == "✓" else f"[yellow]{dcwf_status}[/]")
    
    artifacts_status = "✓" if settings.artifacts_store_name else "✗"
    table.add_row("Artifacts Store", settings.artifacts_store_name or "Not set", f"[green]{artifacts_status}[/]" if artifacts_status == "✓" else f"[yellow]{artifacts_status}[/]")
    
    console.print(table)


if __name__ == "__main__":
    app()
