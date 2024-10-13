import boto3
from torch.utils.data import DataLoader
import torch
import os
import json
from tqdm import tqdm
from PIL import Image
import matplotlib.pyplot as plt
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('.'))))

from sache import SpecifiedHookedViT
from vitact.filedataset import FilePathDataset
from vitact.download import download_laion

def download_sae_checkpoints(sae_checkpoints, base_dir='cruft'):
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET')
    )

    local_files = {}
    for checkpoint in sae_checkpoints:
        layer = int(checkpoint.split('/')[-2].split('_')[0])

        local_path = f'{base_dir}/{"-".join(checkpoint.split("/")[-3:])}'

        local_files[(layer, 'resid')] = local_path

        if not os.path.exists(local_path):

            print(f'Downloading {checkpoint} to {local_path}...')

            s3_client.download_file(
                checkpoint.split('/')[2],
                '/'.join(checkpoint.split('/')[3:]),
                local_path
            )
    
    return local_files

def generate_latents(
        sae_paths,
        dataloader,
        n_activations=250_000,
        batch_size=2048,
        num_top=9,
        transformer_name='laion/CLIP-ViT-L-14-laion2B-s32B-b82K',
        hook_name="resid",
        device='cuda',
        image_dir='cruft/top9',
        n_features=None,
        sequence_idx=0
    ):

    # Prepare locations and load SAEs
    locations = list(sae_paths.keys())
    transformer = SpecifiedHookedViT(locations, transformer_name, device=device)
    sae_dict = {}
    for location, sae_path in sae_paths.items():
        sae = torch.load(sae_path, map_location=device)
        sae_dict[location] = sae

    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    num_features_dict = {}
    topk_values_dict = {}
    topk_indices_dict = {}
    cumulative_file_paths = []
    cumulative_index = 0

    with torch.no_grad():
        for i, (paths, batch) in tqdm(enumerate(dataloader), total=n_activations // batch_size):
            activations = transformer.all_activations(batch)
            current_batch_size = batch.size(0)  # Avoid shadowing the outer batch_size
            current_indices = torch.arange(cumulative_index, cumulative_index + current_batch_size, dtype=torch.long, device=device)
            cumulative_index += current_batch_size

            cumulative_file_paths.extend(paths)

            for location in locations:
                layer, hook_name = location
                sae = sae_dict[location]
                activation = activations[location]
                activation = activation[:, sequence_idx]

                latent = sae.forward_descriptive(activation)['latent']
                latent = latent.detach()

                if location not in num_features_dict:
                    actual_num_features = latent.size(1)
                    if n_features is not None:
                        num_features = min(n_features, actual_num_features)
                    else:
                        num_features = actual_num_features
                    num_features_dict[location] = num_features
                    topk_values_dict[location] = torch.full((num_features, num_top), float('-inf'), device=device)
                    topk_indices_dict[location] = torch.full((num_features, num_top), -1, dtype=torch.long, device=device)

                # Only process up to num_features
                num_features = num_features_dict[location]
                latent = latent[:, :num_features]

                current_values = latent.t()  # shape: [num_features, batch_size]
                current_indices_expanded = current_indices.unsqueeze(0).expand(num_features, -1)

                # Concatenate with previous topk
                total_values = torch.cat((topk_values_dict[location], current_values), dim=1)
                total_indices = torch.cat((topk_indices_dict[location], current_indices_expanded), dim=1)

                # Compute topk
                topk = torch.topk(total_values, k=num_top, dim=1)
                topk_values_dict[location] = topk.values
                indices_in_total = topk.indices

                topk_global_indices = torch.gather(total_indices, 1, indices_in_total)
                topk_indices_dict[location] = topk_global_indices

            if (i + 1) * batch_size >= n_activations:
                break

    for location in locations:
        layer, hook_name = location
        num_features = num_features_dict[location]
        topk_values = topk_values_dict[location]
        topk_indices = topk_indices_dict[location]

        layer_dir = os.path.join(image_dir, f'layer_{layer}_{hook_name}')
        if not os.path.exists(layer_dir):
            os.makedirs(layer_dir)
        print(f'Saving images to: {layer_dir}')

        for feature_idx in tqdm(range(num_features), desc=f'Processing features for layer {layer}'):

            if topk_values[feature_idx].min() <= 0:
                continue

            indices = topk_indices[feature_idx].tolist()
            values = topk_values[feature_idx].tolist()
            file_paths = [cumulative_file_paths[idx] for idx in indices]

            result = {
                'indices': indices,
                'values': values,
                'file_paths': file_paths
            }

            feature_dir = os.path.join(layer_dir, f'feature_{feature_idx}')
            if not os.path.exists(feature_dir):
                os.makedirs(feature_dir)

            with open(os.path.join(feature_dir, f'{feature_idx}_top{num_top}.json'), 'w') as f:
                json.dump(result, f)

            # Load the images
            images = []
            for i, path in enumerate(file_paths):
                if i >= num_top:
                    break
                try:
                    img = Image.open(path).convert('RGB')  # Ensure image is in RGB
                    images.append(img)
                except Exception as e:
                    print(f'Error loading image {path}: {e}')

            # Save individual images
            for i, img in enumerate(images):
                img_path = os.path.join(feature_dir, f'{feature_idx}_top{num_top}_{i}.png')
                img.save(img_path)

            # Plot the images in a grid (adjust grid size based on num_top)
            fig, axes = plt.subplots(3, 3, figsize=(9, 9))
            for ax, img in zip(axes.flatten(), images):
                ax.imshow(img)
                ax.axis('off')
            plt.tight_layout()
            grid_path = os.path.join(feature_dir, f'{feature_idx}_grid.png')
            plt.savefig(grid_path)
            plt.close(fig)

            print(f'Saved images for feature {feature_idx} in layer {layer}')


if __name__ == '__main__':

    sae_checkpoints = [
        's3://sae-activations/log/CLIP-ViT-L-14/11_resid/11_resid_6705c9/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/14_resid/14_resid_6d8202/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/17_resid/17_resid_e0766f/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/20_resid/20_resid_5998fd/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/22_resid/22_resid_8fa3ab/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/2_resid/2_resid_29c579/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/5_resid/5_resid_79d8c9/600023040.pt',
        's3://sae-activations/log/CLIP-ViT-L-14/8_resid/8_resid_9a2c60/600023040.pt',
    ]

    image_dir = 'cruft/top9'

    if os.path.exists(image_dir):
        raise ValueError(f"Output directory {image_dir} already exists. Please remove it before running this script.")

    base_dir = 'cruft'
    laion_img_dir = 'cruft/bench'

    if not os.path.exists(laion_img_dir):
        download_laion(
            n_urls=100_000,
            processes_count=16,
            thread_count=32,
            image_size=224,
            base_dir=base_dir,
            output_dir=laion_img_dir
        )
    else:
        print(f"Skipping download of images to {laion_img_dir} as the directory already exists.")

    sae_paths = download_sae_checkpoints(sae_checkpoints, base_dir=base_dir)

    ds = FilePathDataset(laion_img_dir)
    batch_size = 384
    dataloader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=3)

    generate_latents(
        sae_paths=sae_paths,
        n_activations=40_000,
        dataloader=dataloader,
        batch_size=batch_size,
        num_top=9,  # Number of top activations to keep
        device='cuda',
        image_dir='cruft/top9',
        n_features=1024, # Specify the number of features you want to process
        sequence_idx=128
    )
