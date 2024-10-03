import os
from tracemalloc import start
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_image(url, folder="downloaded_images"):
    """
    Function to download an image from a URL into a specified folder.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)

    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Extract image name from URL and create a path to save the file
        image_name = url.split("/")[-1]
        file_path = os.path.join(folder, image_name)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"{url} - Download succeeded"
    except Exception as e:
        return f"{url} - Download failed: {str(e)}"

def main(urls, max_workers=20):
    """
    Download images from a list of URLs using multiple threads and report the rate of downloads.
    """
    start_time = time.time()
    overall_start = start_time
    results = []
    # Using ThreadPoolExecutor to manage concurrent downloads
    count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Start the download operations and mark each future with its URL
        future_to_url = {executor.submit(download_image, url): url for url in urls}
        # Process results as they complete
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
                count += 1

                # if count % 10 == 0:
                #     elapsed_time = time.time() - start_time
                #     download_rate = 10 / elapsed_time
                #     print(f"Downloaded {count} URLs in {elapsed_time:.2f} seconds at a rate of {download_rate:.2f} URLs per second")
                #     start_time = time.time()

            except Exception as exc:
                results.append(f"{url} generated an exception: {str(exc)}")


    # Calculate and print the download rate
    elapsed_time = time.time() - overall_start
    download_rate = len(results) / elapsed_time
    print(f"Downloaded {len(results)} URLs in {elapsed_time:.2f} seconds at a rate of {download_rate:.2f} URLs per second @ workers: {max_workers}")

# Example usage:
if __name__ == "__main__":
    urls = []

    with open('cruft/urls.txt', 'r') as file:
        urls = [url.strip() for url in file.readlines()]
    print(f"Downloading {len(urls)} images from the provided URLs...")

    worket_ns = [200, 300]

    urls_at_a_time = 100
    for i, w in enumerate(worket_ns):
        print(f"Starting download with {w} workers")
        url_batch = urls[i*urls_at_a_time:(i+1)*urls_at_a_time]
        main(url_batch, w)




# Downloading 1000 images from the provided URLs...
# Starting download with 1 workers
# Downloaded 100 URLs in 157.32 seconds at a rate of 0.64 URLs per second @ workers: 1
# Starting download with 2 workers
# Downloaded 100 URLs in 78.88 seconds at a rate of 1.27 URLs per second @ workers: 2
# Starting download with 5 workers
# Downloaded 100 URLs in 42.92 seconds at a rate of 2.33 URLs per second @ workers: 5
# Starting download with 10 workers
# Downloaded 100 URLs in 29.26 seconds at a rate of 3.42 URLs per second @ workers: 10
# Starting download with 20 workers
# Downloaded 100 URLs in 28.83 seconds at a rate of 3.47 URLs per second @ workers: 20
# Starting download with 50 workers
# Downloaded 100 URLs in 19.88 seconds at a rate of 5.03 URLs per second @ workers: 50
# Starting download with 100 workers
# Downloaded 100 URLs in 9.89 seconds at a rate of 10.11 URLs per second @ workers: 100