import boto3
import datasets
from torch.utils.data import DataLoader
import torch
import os
import json
from torchvision import transforms
from tqdm import tqdm
import glob
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
        save_every=10,
        batch_size=2048,
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
    latent_dir = "/".join(sae_path.split('/')[:-1]) + f'/latents-{n_steps}'

    if not os.path.exists(latent_dir):
        os.makedirs(latent_dir)

    latents = None
    file_paths = []
    printed = False
    with torch.no_grad():
        for i, (paths, batch) in tqdm(enumerate(dataloader), total=n_activations // batch_size):

            activations = transformer.all_activations(batch)[location]
            activations = activations[:, 0]

            latent = sae.forward_descriptive(activations)['latent']
            if not printed:
                print(torch.sum(latent > 0))
                print(torch.topk(latent, 10))
                printed = True
            
            latent = latent.detach().cpu()

            if latents is None:
                latents = latent
            else:
                latents = torch.cat((latents, latent), dim=0)

            file_paths.extend(paths)


            if i > 0 and i % save_every == 0:
                with open(f'{latent_dir}/file_paths_{i}.json', 'w') as f:
                    json.dump(file_paths, f)
                torch.save(latents, f'{latent_dir}/latents_{i}.pt')
                file_paths = []
                latents = None

            if i * batch_size > n_activations:
                if latents.shape[0] > 0:
                    with open(f'{latent_dir}/file_paths_{i}.json', 'w') as f:
                        json.dump(file_paths, f)
                    torch.save(latents, f'{latent_dir}/latents_{i}.pt')
                break

    return latent_dir


def get_top9(latent_dir, num_top=9, num_features=650, dataset=None):
    if dataset is not None:
        ids =  [int(i) for i in ds['id']]

    file_path_files = sorted(glob.glob(os.path.join(latent_dir, 'file_paths_*.json')))
    latent_files = sorted(glob.glob(os.path.join(latent_dir, 'latents_*.pt')))

    image_dir = os.path.join(latent_dir, 'images')

    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    print('saving images to:', image_dir)

    # Initialize topk values and indices for all features
    topk_values = torch.full((num_features, num_top), float('-inf'))
    topk_indices = torch.full((num_features, num_top), -1, dtype=torch.long)
    topk_file_paths = [[''] * num_top for _ in range(num_features)]
    indices_gt_zero = [[] for _ in range(num_features)]

    cumulative_index = 0  # Keeps track of the global index across batches
    cumulative_file_paths = []

    for batch_num, (fp_file, latent_file) in enumerate(zip(file_path_files, latent_files)):
        print(f'Processing batch {batch_num+1}/{len(latent_files)}')
        with open(fp_file, 'r') as f:
            file_paths = json.load(f)
        latents = torch.load(latent_file)[:, :num_features]  # shape: [batch_size, num_features]
        m = torch.max(latents).item()

        print(m)
        if int(m) == 0:
            continue

        batch_size = latents.size(0)
        current_indices = torch.arange(cumulative_index, cumulative_index + batch_size, dtype=torch.long)
        cumulative_index += batch_size

        cumulative_file_paths.extend(file_paths)

        # Transpose latents to shape [num_features, batch_size]
        current_values = latents.t()  # shape: [num_features, batch_size]

        # Expand current_indices to shape [num_features, batch_size]
        current_indices_expanded = current_indices.unsqueeze(0).expand(num_features, -1)  # shape: [num_features, batch_size]

        # Concatenate current batch with previous topk
        total_values = torch.cat((topk_values, current_values), dim=1)  # shape: [num_features, num_top + batch_size]
        total_indices = torch.cat((topk_indices, current_indices_expanded), dim=1)  # shape: [num_features, num_top + batch_size]

        # Perform topk across the concatenated values
        topk = torch.topk(total_values, k=num_top, dim=1)
        topk_values = topk.values  # shape: [num_features, num_top]
        indices_in_total = topk.indices  # shape: [num_features, num_top]

        # Gather the corresponding global indices
        topk_global_indices = torch.gather(total_indices, 1, indices_in_total)  # shape: [num_features, num_top]

        # Update topk_indices
        topk_indices = topk_global_indices

        # Update topk_file_paths
        for feature_idx in range(num_features):
            indices_in_total_feature = indices_in_total[feature_idx]
            total_file_paths = topk_file_paths[feature_idx] + file_paths
            topk_file_paths[feature_idx] = [total_file_paths[i] for i in indices_in_total_feature.tolist()]

        # Update indices_gt_zero
        mask = current_values > 0  # shape: [num_features, batch_size]
        for feature_idx in range(num_features):
            indices = current_indices[mask[feature_idx]]
            indices_gt_zero[feature_idx].extend(indices.tolist())

    # After processing all batches, save the results
    for feature_idx in tqdm(range(num_features)):

        if topk_values[feature_idx].min() <= 0:
            continue

        result = {
            'indices': topk_indices[feature_idx].tolist(),
            'values': topk_values[feature_idx].tolist(),
            'indices_gt_zero': indices_gt_zero[feature_idx],
            'file_paths': topk_file_paths[feature_idx]
        }

        feature_dir = os.path.join(image_dir, f'feature_{feature_idx}')
        if not os.path.exists(feature_dir):
            os.makedirs(feature_dir)

        with open(os.path.join(feature_dir, f'{feature_idx}_top9.json'), 'w') as f:
            json.dump(result, f)

        # Load the images
        images = []
        for i, path in enumerate(topk_file_paths[feature_idx]):
            if i >= num_top:
                break
            img = Image.open(path)
            images.append(img)

            # Save image
            img.save(os.path.join(feature_dir, f'{feature_idx}_top9_{i}.png'))

        # Plot the images in a 3x3 grid
        fig, axes = plt.subplots(3, 3, figsize=(9, 9))
        for ax, img in zip(axes.flatten(), images):
            ax.imshow(img)
            ax.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(feature_dir, f'{feature_idx}_grid.png'))
        plt.close(fig)

        print(f'Saved images for feature {feature_idx}')

def download_sae_checkpoints(sae_checkpoints):

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET')
    )

    local_files = {}
    for checkpoint in sae_checkpoints:

        layer = int(checkpoint.split('/')[-2].split('_')[0])

        local_path = f'cruft/{"-".join(checkpoint.split("/")[-3:])}'

        local_files[(layer, 'resid')] = local_path

        print(f'Downloading {checkpoint} to {local_path}...')

        s3_client.download_file(
            checkpoint.split('/')[2],
            '/'.join(checkpoint.split('/')[3:]),
            local_path
        )
    
    return local_files

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



# Update DataLoader to use the custom collation function
ds = datasets.load_dataset("lmms-lab/GQA", 'train_all_images')['train']
batch_size = 384
dataloader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=3, collate_fn=collate_fn)

out_dir = generate_latents(
    sae_path='../vitact/cruft/17/200139264.pt',
    n_activations=20000,
    dataloader=dataloader,
    layer=17,
    batch_size=batch_size
)

out_dir = '../vitact/cruft/17/latents-200139264'
get_top9(out_dir, num_top=9, num_features=10000, dataset=ds)