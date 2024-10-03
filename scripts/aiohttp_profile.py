import os
import asyncio
import aiohttp
import aiofiles
import time

async def download_image(session, url, timeout, folder="downloaded_images"):
    """
    Asynchronously download an image from a URL into a specified folder.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)

    try:
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            # Extract image name from URL and create a path to save the file
            image_name = url.split("/")[-1]
            file_path = os.path.join(folder, image_name)

            # Asynchronously write the content to a file
            async with aiofiles.open(file_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    await f.write(chunk)
            return True
    except Exception as e:
        return False

async def main(urls, max_concurrent=1000, timeout=3):
    """
    Asynchronously download images from a list of URLs and report the rate of downloads.
    """
    start_time = time.time()
    results = []

    # Semaphore to limit the number of concurrent downloads
    semaphore = asyncio.Semaphore(max_concurrent)

    succeeded = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            async def sem_task(url):
                async with semaphore:
                    return await download_image(session, url, timeout)
            tasks.append(asyncio.create_task(sem_task(url)))

        # Process results as they complete
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            if result:
                succeeded += 1

    # Calculate and print the download rate
    elapsed_time = time.time() - start_time
    download_rate = succeeded / elapsed_time
    print(f"Downloaded {len(results)} URLs in {elapsed_time:.2f} seconds at a rate of {download_rate:.2f} URLs per second")

# Example usage:
if __name__ == "__main__":
    urls = []

    with open('cruft/urls.txt', 'r') as file:
        urls = [url.strip() for url in file.readlines()]
    timeouts = [3, 5, 9, 15]

    urls_at_a_time = 200
    for i, w in enumerate(timeouts):
        print(f"Starting download with {w} workers")
        url_batch = urls[i*urls_at_a_time:(i+1)*urls_at_a_time]
        asyncio.run(main(url_batch, timeout=w, max_concurrent=200))
