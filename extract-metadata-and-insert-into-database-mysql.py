import os
from PIL import Image
import hashlib
import mysql.connector


# Function to extract metadata categories and subcategories
def get_image_metadata(image_path):
    try:
        with Image.open(image_path) as img:
            metadata = img.info
        return metadata
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {}


def extract_metadata_from_parameter(metadata_str, image_path):
    metadata_dict = {}

    hashermd5 = hashlib.md5()
    hashersha1 = hashlib.sha1()
    hashersha256 = hashlib.sha256()

    # Get Hash values
    with open(image_path, "rb") as file:
        while True:
            chunk = file.read(4096)  # Read in 4KB chunks
            if not chunk:
                break
            hashermd5.update(chunk)
            hashersha1.update(chunk)
            hashersha256.update(chunk)

    hash_md5 = hashermd5.hexdigest()
    hash_sha1 = hashersha1.hexdigest()
    hash_sha256 = hashersha256.hexdigest()
    metadata_dict["MD5"] = hash_md5
    metadata_dict["SHA1"] = hash_sha1
    metadata_dict["SHA256"] = hash_sha256

    # Add filename, directory, and file size to the metadata
    file_name = os.path.basename(image_path)
    directory = os.path.dirname(image_path)
    file_size = os.path.getsize(image_path)
    metadata_dict["File Name"] = file_name.strip(".png")
    metadata_dict["Directory"] = directory.rsplit('/', 2)[-1]
    metadata_dict["File Size"] = file_size

    # Split by the first occurrence of "Negative prompt" or "Steps"
    negative_prompt_index = metadata_str.find("Negative prompt:")
    steps_index = metadata_str.find("Steps:")

    if negative_prompt_index != -1:
        positive_prompt = metadata_str[:negative_prompt_index].strip()
        metadata_dict["Positive prompt"] = positive_prompt

        remaining_content = metadata_str[negative_prompt_index:].strip()
        negative_prompt_end = remaining_content.find("Steps:")

        if negative_prompt_end != -1:
            negative_prompt = remaining_content[len("Negative prompt:"):negative_prompt_end].strip()
            metadata_dict["Negative prompt"] = negative_prompt
        else:
            metadata_dict["Negative prompt"] = remaining_content

        steps_section = metadata_str[steps_index:].strip()
        metadata_dict["Steps"] = steps_section

        # Split the content after "Steps:" into key-value pairs
        content_segments = steps_section.split(", ")
        for segment in content_segments:
            key_value = segment.split(": ", 1)
            if len(key_value) == 2:
                key, value = key_value[0], key_value[1]
                metadata_dict[key] = value
    elif steps_index != -1:
        positive_prompt = metadata_str[:steps_index].strip()
        metadata_dict["Positive prompt"] = positive_prompt

        steps_section = metadata_str[steps_index:].strip()
        metadata_dict["Steps"] = steps_section

        # Split the content after "Steps:" into key-value pairs
        content_segments = steps_section.split(", ")
        for segment in content_segments:
            key_value = segment.split(": ", 1)
            if len(key_value) == 2:
                key, value = key_value[0], key_value[1]
                metadata_dict[key] = value
    else:
        # If neither "Negative prompt" nor "Steps" is found, consider the entire section as "Positive prompt"
        metadata_dict["Positive prompt"] = metadata_str

    return metadata_dict


# Function to create a MySQL database and table
def connect_database(database_name):
    conn = mysql.connector.connect(
        host="your_host",
        user="your_username",
        password="your_password",
        database=database_name
    )
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ImageMetadata (
            id INT AUTO_INCREMENT PRIMARY KEY,
            FileName VARCHAR(255),
            Directory TEXT,
            FileSize TEXT,
            PositivePrompt TEXT,
            NegativePrompt TEXT,
            Steps TEXT,
            Sampler TEXT,
            CFGScale TEXT,
            Seed TEXT,
            ImageSize TEXT,
            ModelHash TEXT,
            Model TEXT,
            SeedResizeFrom TEXT,
            DenoisingStrength TEXT,
            Version TEXT,
            MD5 TEXT,
            SHA1 TEXT,
            SHA256 TEXT
        )
    ''')
    conn.commit()
    return conn


# Function to insert metadata into the MySQL database if it doesn't already exist
def insert_metadata_into_database(conn, metadata):
    cursor = conn.cursor()

    # Check if the combination of FileName and Directory already exists in the database
    query = '''
    SELECT COUNT(*) FROM ImageMetadata
    WHERE SHA256 = %s
    '''
    cursor.execute(query, (metadata.get('SHA256', ''),))
    result = cursor.fetchone()

    if result[0] == 0:
        # The combination doesn't exist, so insert the metadata
        cursor.execute('''
            INSERT INTO ImageMetadata (
                FileName, Directory, FileSize, PositivePrompt, NegativePrompt, Steps, Sampler, CFGScale, Seed, 
                ImageSize, ModelHash, Model, SeedResizeFrom, DenoisingStrength, Version, MD5, SHA1, SHA256
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            metadata.get('File Name', ''),
            metadata.get('Directory', ''),
            metadata.get('File Size', ''),
            metadata.get('Positive prompt', ''),
            metadata.get('Negative prompt', ''),
            metadata.get('Steps', ''),
            metadata.get('Sampler', ''),
            metadata.get('CFG scale', ''),
            metadata.get('Seed', ''),
            metadata.get('Size', ''),
            metadata.get('Model hash', ''),
            metadata.get('Model', ''),
            metadata.get('Seed resize from', ''),
            metadata.get('Denoising strength', ''),
            metadata.get('Version', ''),
            metadata.get('MD5', ''),
            metadata.get('SHA1', ''),
            metadata.get('SHA256', '')
        ))
        conn.commit()
        print(f"Metadata from {metadata.get('File Name', '')} extracted and added to the database.")
    else:
        # The combination already exists, so skip the insert
        print(f"Metadata from {metadata.get('File Name', '')} already exists in the database. Skipping insert.")


# Folder containing images
image_folder = 'path/to/your/image/folder'

# MySQL database configuration
database_name = 'image_metadata'

# Create a MySQL database and table if it doesn't exist
conn = connect_database(database_name)

# Loop through the images in the folder
for filename in os.listdir(image_folder):
    if filename.endswith('.png'):
        image_path = os.path.join(image_folder, filename)
        metadata = get_image_metadata(image_path)
        parameters_metadata = metadata.get("parameters", "")
        extracted_metadata = extract_metadata_from_parameter(parameters_metadata, image_path)

        if extracted_metadata is not None:
            insert_metadata_into_database(conn, extracted_metadata)

# Close the database connection
conn.close()
