import boto3
import datasets
from torch.utils.data import DataLoader
import torch
import os
import json
from torchvision import transforms
from tqdm import tqdm
from PIL import Image
import matplotlib.pyplot as plt
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('.'))))

from sache import SpecifiedHookedViT
from vitact.tardataset import StreamingTensorDataset 


transform = transforms.Compose([
    transforms.ToTensor(),  # Convert PIL image to a tensor
])

def collate_fn(batch):
    images = []
    ids = []
    for item in batch:
        ids.append(item['id'])
        img = item['image']
        # if image is black and white, convert to RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')

        img = img.resize((224, 224))
        images.append(transform(img))
    images = torch.stack(images)  # Stack images into a single tensor
    
    return ids, images

def generate_latents(
        sae_path,
        dataloader,
        n_activations=250_000,
        batch_size=2048,
        num_top=9,
        transformer_name='laion/CLIP-ViT-L-14-laion2B-s32B-b82K',
        hook_name="resid",
        layer=22,
        device='cuda',
    ):

    location = (layer, hook_name)
    transformer = SpecifiedHookedViT([location], transformer_name, device=device)
    sae = torch.load(sae_path, map_location=device)

    print(type(sae))
    
    n_steps = sae_path.split('/')[-1].split('.')[0]
    image_dir = "/".join(sae_path.split('/')[:-1]) + f'/images-{n_steps}'

    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    num_features = None
    topk_values = None
    topk_indices = None
    cumulative_file_paths = []
    cumulative_index = 0

    with torch.no_grad():
        for i, (paths, batch) in tqdm(enumerate(dataloader), total=n_activations // batch_size):

            activations = transformer.all_activations(batch)[location]
            activations = activations[:, 0]

            latent = sae.forward_descriptive(activations)['latent']
            latent = latent.detach()

            if num_features is None:
                num_features = latent.size(1)
                topk_values = torch.full((num_features, num_top), float('-inf'), device=device)
                topk_indices = torch.full((num_features, num_top), -1, dtype=torch.long, device=device)

            batch_size = latent.size(0)
            current_indices = torch.arange(cumulative_index, cumulative_index + batch_size, dtype=torch.long, device=device)
            cumulative_index += batch_size

            cumulative_file_paths.extend(paths)

            current_values = latent.t()  # shape: [num_features, batch_size]

            current_indices_expanded = current_indices.unsqueeze(0).expand(num_features, -1)  # shape: [num_features, batch_size]

            # Concatenate with previous topk
            total_values = torch.cat((topk_values, current_values), dim=1)
            total_indices = torch.cat((topk_indices, current_indices_expanded), dim=1)

            # Compute topk
            topk = torch.topk(total_values, k=num_top, dim=1)
            topk_values = topk.values
            indices_in_total = topk.indices

            topk_global_indices = torch.gather(total_indices, 1, indices_in_total)
            topk_indices = topk_global_indices

            if i * batch_size >= n_activations:
                break

    # After processing all batches, create grids
    for feature_idx in tqdm(range(num_features)):

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

        feature_dir = os.path.join(image_dir, f'feature_{feature_idx}')
        if not os.path.exists(feature_dir):
            os.makedirs(feature_dir)

        with open(os.path.join(feature_dir, f'{feature_idx}_top{num_top}.json'), 'w') as f:
            json.dump(result, f)

        # Load the images
        images = []
        for i, path in enumerate(file_paths):
            if i >= num_top:
                break
            img = Image.open(path)
            images.append(img)

            # Save image
            img.save(os.path.join(feature_dir, f'{feature_idx}_top{num_top}_{i}.png'))

        # Plot the images in a 3x3 grid
        fig, axes = plt.subplots(3, 3, figsize=(9, 9))
        for ax, img in zip(axes.flatten(), images):
            ax.imshow(img)
            ax.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(feature_dir, f'{feature_idx}_grid.png'))
        plt.close(fig)

        print(f'Saved images for feature {feature_idx}')

# Example usage:
# Update DataLoader to use the custom collation function
ds = datasets.load_dataset("lmms-lab/GQA", 'train_all_images')['train']
batch_size = 384
dataloader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=3, collate_fn=collate_fn)

generate_latents(
    sae_path='../vitact/cruft/17/200139264.pt',
    n_activations=20000,
    dataloader=dataloader,
    layer=17,
    batch_size=batch_size,
    num_top=9  # Number of top activations to keep
)
