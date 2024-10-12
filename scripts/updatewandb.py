import wandb
api = wandb.Api()
runs = api.runs("lewington/CLIP-ViT-L-14-sae")

for run in runs:
    print(run)
    print(run.name)
    print(run.config)
    if "layer" not in run.config.keys():
        run.config["layer"] = int(run.name.split("_")[0])
        run.update()