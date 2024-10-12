import wandb
from wandb import Api
import os
import shutil
import tempfile
import argparse

def copy_wandb_runs(
    source_entity,
    source_project,
    target_entity,
    target_project,
    api_key=None,
    copy_artifacts=True
):
    """
    Copies all runs from the source wandb project to the target project.

    :param source_entity: The wandb entity (user or team) of the source project.
    :param source_project: Name of the source wandb project.
    :param target_entity: The wandb entity (user or team) of the target project.
    :param target_project: Name of the target wandb project.
    :param api_key: (Optional) Your wandb API key. If not provided, it will use the default authentication.
    :param copy_artifacts: Whether to copy artifacts. Defaults to True.
    """
    # Authenticate with wandb
    if api_key:
        api = Api(api_key=api_key)
    else:
        api = Api()  # Uses the default wandb authentication

    # Get the source and target projects
    try:
        source_proj = api.project(source_entity, source_project)
    except Exception as e:
        print(f"Error accessing source project '{source_entity}/{source_project}': {e}")
        return

    try:
        target_proj = api.project(target_entity, target_project)
    except wandb.errors.CommError:
        # If target project does not exist, create it
        print(f"Target project '{target_entity}/{target_project}' does not exist. Creating it...")
        try:
            target_proj = api.create_project(target_entity, target_project)
            print(f"Created target project '{target_entity}/{target_project}'.")
        except Exception as e:
            print(f"Failed to create target project: {e}")
            return
    except Exception as e:
        print(f"Error accessing target project '{target_entity}/{target_project}': {e}")
        return

    # Fetch all runs from the source project
    try:
        runs = api.runs(f"{source_entity}/{source_project}")
        print(f"Found {len(runs)} runs in the source project '{source_entity}/{source_project}'.")
    except Exception as e:
        print(f"Error fetching runs from source project: {e}")
        return

    for run in runs:
        print(f"Copying run: {run.id} - {run.name}")
        # Start a new run in the target project
        with wandb.init(project=target_project, entity=target_entity, name=run.name, config=run.config, resume=False, allow_val_change=True) as new_run:
            # Log parameters
            params = run.config
            if params:
                for key, value in params.items():
                    wandb.config[key] = value

            # Log tags
            tags = run.tags
            if tags:
                for tag in tags:
                    wandb.run.tags.add(tag)

            # Log metrics
            history = run.history(pandas=False)
            for entry in history:
                for key, value in entry.items():
                    if key not in ['_step', '_runtime']:
                        wandb.log({key: value}, step=entry.get('_step', None))

            # Handle artifacts
            if copy_artifacts and run.logged_artifacts:
                for artifact in run.logged_artifacts():
                    print(f"  Copying artifact: {artifact.name} (type: {artifact.type})")
                    # Download the artifact
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        local_path = artifact.download(root=tmp_dir)
                        # Log the artifact to the target project
                        # Re-create the artifact with the same name and type
                        new_artifact = wandb.Artifact(name=artifact.name, type=artifact.type)
                        new_artifact.add_dir(local_path)
                        wandb.log_artifact(new_artifact)
            else:
                print("  No artifacts to copy or artifact copying disabled.")

    print("All runs have been copied successfully.")

if __name__ == "__main__":
    copy_wandb_runs(
        source_entity='lewington',
        source_project='test-vit-sae-multilayer',
        target_entity='lewington',
        target_project='CLIP-ViT-L-14-sae',
        api_key=os.getenv("WANDB_API_KEY"),
        copy_artifacts=False
    )
