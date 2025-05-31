import requests
import shutil
from PIL import Image, ImageOps
from tqdm import tqdm

API_KEY = "key"
IMMICH_ADDRESS = "http://192.168.100.45:2283"
personId = "df5421a4-f992-47f4-881e-b024c2e19a4e"
IMG_FILE_TYPES = ["jpg", "JPG", "png", "PNG"]
# ffmpeg -r 15 -i "norm/%d.jpg" -vf reverse movie.mp4


def fetch_buckets(personId):

    url = f"{IMMICH_ADDRESS}/api/timeline/buckets?personId={personId}"
    headers = {"Accept": "application/json", "x-api-key": API_KEY}

    response = requests.request("GET", url, headers=headers).json()
    return response

def get_bucket(personId, bucketTime):
    url = f"{IMMICH_ADDRESS}/api/timeline/bucket?timeBucket={bucketTime}&personId={personId}"

    headers = {"Accept": "application/json", "x-api-key": API_KEY}

    response = requests.request("GET", url, headers=headers).json()
    return response

def download(id, filename):
    url = f"{IMMICH_ADDRESS}/api/assets/{id}/original"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "Accept": "application/octet-stream",
    }

    response = requests.request("GET", url, headers=headers, stream=True)
    with open("data/" + filename, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)

def getAssetInfo(id):
    url = f"{IMMICH_ADDRESS}/api/assets/{id}"

    headers = {"Accept": "application/json", "x-api-key": API_KEY}

    response = requests.request("GET", url, headers=headers).json()
    return response

def getFace(id, personId):
    url = f"{IMMICH_ADDRESS}/api/faces?id={id}"

    headers = {"Accept": "application/json", "x-api-key": API_KEY}

    response = requests.request("GET", url, headers=headers).json()

    for face in response:
        if face["person"] is not None and face["person"]["id"] == personId:
            return face

    return None

def normalize_image(img_path, rel_rect, target_rect, output_size):
    img = Image.open(img_path)
    img = ImageOps.exif_transpose(img)
    w, h = img.size

    # Convert relative coordinates to absolute pixels
    rx1, ry1, rx2, ry2 = rel_rect
    x1 = int(rx1 * w)
    y1 = int(ry1 * h)
    x2 = int(rx2 * w)
    y2 = int(ry2 * h)
    target_x, target_y, target_width, target_height = target_rect

    rect_width = x2 - x1
    rect_height = y2 - y1

    scale_x = target_width / rect_width
    scale_y = target_height / rect_height

    # Open and scale image
    new_size = (int(img.width * scale_x), int(img.height * scale_y))
    img_scaled = img.resize(new_size, Image.BILINEAR)

    # Offset calculation
    new_x1 = x1 * scale_x
    new_y1 = y1 * scale_y
    offset_x = int(target_x - new_x1)
    offset_y = int(target_y - new_y1)

    # Create a blank canvas and paste the transformed image
    canvas = Image.new("RGB", output_size, (0, 0, 0))
    canvas.paste(img_scaled, (offset_x, offset_y))

    return canvas

buckets = fetch_buckets(personId)

frame = 0
for bucket in tqdm(buckets):

    bucket = get_bucket(personId, bucket["timeBucket"])
    for i, id in enumerate(bucket["id"]):
        
        info = getAssetInfo(id)
        filename = info["originalFileName"]
        face = getFace(id, personId)

        if face is not None and filename.split(".")[-1] in IMG_FILE_TYPES:

            download(id, filename)
            w, h = face["imageWidth"], face["imageHeight"]

            rect = (
                face["boundingBoxX1"] / w,
                face["boundingBoxY1"] / h,
                face["boundingBoxX2"] / w,
                face["boundingBoxY2"] / h,
            )
            target_rect = (960 - 100, 540 - 100, 200, 200)

            output_size = (1920, 1080)
            normalized = normalize_image(
                f"data/{filename}", rect, target_rect, output_size
            )
            normalized.save(f"norm/{frame}.jpg")
            frame += 1
