import os
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import mysql.connector
import yaml


def read_configuration():
    try:
        with open("metadata_config.yml", "r") as config_file:
            return yaml.safe_load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError("metadata_config.yml file not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML in metadata_config.yml: {e}")


def create_logger(
    name, log_file, logs_directory, prefix, level=logging.DEBUG, max_log_size=10 * 1024 * 1024
):
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    all_file_handler = RotatingFileHandler(
        os.path.join(logs_directory, f"{prefix}{name.capitalize()}.log"),
        maxBytes=max_log_size,
        backupCount=5,
    )
    all_file_handler.setFormatter(formatter)
    all_file_handler.setLevel(level)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(all_file_handler)

    return logger


def configure_loggers():
    config = read_configuration()
    level = config["level"]
    logs_directory = config["logs_directory"]
    prefix = config["prefix"]
    max_log_size = 10 * 1024 * 1024  # 10MB
    year = str(datetime.now().strftime("%Y"))
    month = str(datetime.now().strftime("%m"))
    day = str(datetime.now().strftime("%d"))
    date = f"{year}-{month}-{day}"
    directory_path = os.path.join(logs_directory, year, month, day)
    os.makedirs(directory_path, exist_ok=True)

    info_logger = create_logger(
        "info",
        os.path.join(directory_path, f"{date}-{prefix}Info.log"),
        logs_directory,
        prefix,
        level,
        max_log_size,
    )
    extraction_logger = create_logger(
        "extraction",
        os.path.join(directory_path, f"{date}-{prefix}Extraction.log"),
        logs_directory,
        prefix,
        level,
        max_log_size,
    )
    debug_logger = create_logger(
        "debug",
        os.path.join(directory_path, f"{date}-{prefix}Debug.log"),
        logs_directory,
        prefix,
        level,
        max_log_size,
    )

    return info_logger, extraction_logger, debug_logger


# Function to extract metadata categories and subcategories
def get_image_metadata(image_path, info_logger):
    try:
        with Image.open(image_path) as img:
            raw_metadata = img.info
            if raw_metadata is not None:
                metadata = raw_metadata.get("parameters", "")
                if metadata is not None:
                    return metadata
    except Exception as e:
        info_logger.error(f"An error occurred: {str(e)}")


def extract_metadata_from_parameter(
    metadata, image_path, nsfw, info_logger, debug_logger
):
    metadata_dict = {}

    # Add filename, directory, and file size to the metadata
    file_name = os.path.basename(image_path).strip(".png")
    directory = os.path.basename(os.path.dirname(image_path))
    file_size = os.path.getsize(image_path)
    creation_time = datetime.fromtimestamp(os.path.getctime(image_path))
    metadata_dict["FileName"] = file_name
    metadata_dict["Directory"] = directory
    metadata_dict["FileSize"] = file_size
    metadata_dict["CreatedAt"] = creation_time.strftime("%Y-%m-%d %H:%M:%S")

    # Split by the first occurrence of "Negative prompt" or "Steps"
    negative_prompt_index = metadata.find("Negative prompt:")
    steps_index = metadata.find("Steps:")

    if negative_prompt_index != -1:
        positive_prompt = metadata[:negative_prompt_index].strip()
        metadata_dict["PositivePrompt"] = positive_prompt

        remaining_content = metadata[negative_prompt_index:].strip()
        negative_prompt_end = remaining_content.find("Steps:")

        if negative_prompt_end != -1:
            negative_prompt = remaining_content[
                len("Negative prompt:") : negative_prompt_end
            ].strip()
            metadata_dict["NegativePrompt"] = negative_prompt
        else:
            metadata_dict["NegativePrompt"] = remaining_content

        steps_section = metadata[steps_index:].strip()
        metadata_dict["Steps"] = steps_section

        # Split the content after "Steps:" into key-value pairs
        content_segments = steps_section.split(", ")
        for segment in content_segments:
            debug_logger.debug(f"Key-value pair: {segment}")
            key_value = segment.split(": ", 1)
            if len(key_value) == 2:
                key, value = key_value[0], key_value[1]
                metadata_dict[key] = value
            else:
                debug_logger.warning(f"Invalid key-value pair: {segment}. Ignoring...")
    elif steps_index != -1:
        positive_prompt = metadata[:steps_index].strip()
        metadata_dict["PositivePrompt"] = positive_prompt

        steps_section = metadata[steps_index:].strip()
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
        metadata_dict["PositivePrompt"] = metadata

    # Add NSFW values
    if nsfw:
        import opennsfw2 as n2

        try:
            img = Image.open(image_path)
            img.thumbnail((512, 512))

            nsfw_probability = n2.predict_image(image_path)
            if nsfw_probability is None:
                info_logger.error(f"NSFW Probability is None.")
                return {}

            debug_logger.info(
                f"NSFWProbability for image '{os.path.basename(image_path)}' is {nsfw_probability}"
            )
            metadata_dict["NSFWProbability"] = nsfw_probability
        except OSError as e:
            debug_logger.warning(
                f"Skipping image '{os.path.basename(image_path)}' due to an error: {str(e)}"
            )
    else:
        nsfw_probability = ""
        metadata_dict["NSFWProbability"] = nsfw_probability
        debug_logger.info("NSFW is off so no nsfw calculation")

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

    if metadata_dict is not None:
        return metadata_dict


# Function to create a MySQL database and table
def connect_database(host, user, password, database_name, info_logger):
    try:
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database_name
        )
        if conn is not None:
            info_logger.debug(f"Connected to MySQL database: {database_name}")
            return conn
        else:
            info_logger.error("Failed to connect to the database")
    except mysql.connector.Error as e:
        info_logger.error(f"Failed to connect to the database: {e}")


def update_database_table(conn, table_name, columns, info_logger):
    cursor = conn.cursor()
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    table_exists = cursor.fetchone()[0]
    if table_exists is None:
        # Create the table if it doesn't exist
        column_definitions = ", ".join([f"{column} TEXT" for column in columns])
        create_table_query = f"""
        CREATE TABLE {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {column_definitions}
        )
        """

        try:
            cursor.execute(create_table_query)
            conn.commit()
            info_logger.info(f"Table {table_name} created successfully.")
        except mysql.connector.Error as e:
            info_logger.error(f"Table creation could not be executed: {e}")
        finally:
            cursor.close()


def update_database_columns(conn, table_name, columns, info_logger):
    # Check and add columns if they do not exist
    cursor = conn.cursor()

    cursor.execute(f"DESCRIBE {table_name}")
    existing_columns = [column[0] for column in cursor.fetchall()]

    for column in columns:
        if column not in existing_columns:
            # Add the column if it does not exist
            add_column_query = f"ALTER TABLE {table_name} ADD COLUMN {column} TEXT"
            try:
                cursor.execute(add_column_query)
                conn.commit()
                info_logger.info(f"Column {column} added successfully.")
            except mysql.connector.Error as e:
                info_logger.error(f"Error adding column {column}: {e}")
            finally:
                cursor.close()


def check_if_metadata_exists(conn, metadata, table_name, debug_logger):
    cursor = conn.cursor()

    # Check if the data already exists in the database
    query = f"""
    SELECT COUNT(*) FROM {table_name}
    WHERE SHA256 = %s
    """
    cursor.execute(query, (metadata.get("SHA256", ""),))
    row_count = cursor.fetchone()[0]
    if row_count:
        debug_logger.info(f"Number of rows with the same SHA256 value: {row_count}")
    else:
        row_count = 0
        debug_logger.info("No existing record found.")

    return row_count


def check_if_metadata_equal(
    conn, metadata, table_name, columns, info_logger, debug_logger
):
    cursor = conn.cursor()

    # Build the SELECT query and extract columns for existing metadata
    select_columns = ", ".join(columns)
    query = f"""
        SELECT {select_columns}
        FROM {table_name}
        WHERE SHA256 = %s
    """

    try:
        cursor.execute(query, (metadata.get("SHA256", ""),))
        result = cursor.fetchone()

        if result:
            existing_metadata = {columns[i]: result[i] for i in range(len(columns))}

            # Check if the metadata is equal
            equal_values = all(
                metadata[key] == str(existing_metadata[key]) for key in columns
            )

            if equal_values:
                debug_logger.info("Metadata is already in the database and is equal.")
                return True
            else:
                debug_logger.info("Metadata in the database is different. Comparison:")
                for column in columns:
                    debug_logger.info(
                        f"{column} : {metadata.get(column, 'N/A')}  |  {column} : {existing_metadata.get(column, 'N/A')}"
                    )

                return False
        else:
            debug_logger.info("No existing record found for metadata.")
            return True  # Consider it not equal as there is no existing record
    except Exception as e:
        info_logger.error(f"Error checking metadata equality: {e}")
    finally:
        cursor.close()


# Function to insert metadata into the MySQL database if it doesn't already exist
def insert_metadata_into_database(
    conn, metadata, table_name, columns, info_logger, extraction_logger
):
    cursor = conn.cursor()

    column_names = ", ".join(columns)
    value_placeholders = ", ".join(["%s" for _ in columns])
    try:
        # Build and execute the SQL query
        query = f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({value_placeholders})
        """

        # Extract values from metadata based on column order
        values = [metadata.get(column, "") for column in columns]

        cursor.execute(query, values)
        conn.commit()
        extraction_logger.info(
            f"Metadata from {metadata.get('File Name', '')} in folder {metadata.get('Directory', '')} extracted and added to the database."
        )
    except Exception as e:
        info_logger.error(
            f"Error while inserting metadata into database from {metadata.get('File Name', '')} in folder {metadata.get('Directory', '')}. Error: {e}"
        )
    finally:
        cursor.close()


def update_metadata_in_database(
    conn, metadata, table_name, columns, info_logger, extraction_logger
):
    cursor = conn.cursor()

    # Build the SET clause for updating
    set_clause = ", ".join([f"{column} = %s" for column in columns])

    try:
        # Build and execute the SQL query
        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE SHA256 = %s
        """

        # Extract values from metadata based on column order
        values = [metadata.get(column, "") for column in columns]
        values.append(metadata.get("SHA256", ""))  # Append SHA256 for WHERE condition

        cursor.execute(query, values)
        conn.commit()

        extraction_logger.info(
            f"Metadata for {metadata.get('File Name', '')} in folder {metadata.get('Directory', '')} has been updated in the database."
        )
    except Exception as e:
        info_logger.error(
            f"Failed to update metadata for {metadata.get('File Name', '')} in folder {metadata.get('Directory', '')} in the database. Error: {e}"
        )
    finally:
        cursor.close()


def start_metadata_extractor():
    start_time = datetime.now()
    info_logger, extraction_logger, debug_logger = configure_loggers()
    info_logger.debug(f"Loggers successfully initialized")
    try:
        try:
            info_logger.info("Script started.")
            config = read_configuration()
            host = config["host"]
            user = config["user"]
            password = config["password"]
            database_name = config["database_name"]
            table_name = config["table_name"]
            image_folder = Path(config["image_folder"])
            use_yesterday = config.get("use_yesterday", False)
            nsfw = config.get("nsfw_probability", True)

            info_logger.info(
                f"Host: {host}, User: {user}, Password: {password}, Database: {database_name}, Table: {table_name}, Image Folder: {image_folder}, Use Yesterday: {use_yesterday}, NSFW: {nsfw}"
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

        if use_yesterday:
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            formatted_yesterday = yesterday.strftime("%Y-%m-%d")
            image_folder = os.path.join(image_folder, formatted_yesterday)

        columns = [
            "FileName",
            "Directory",
            "FileSize",
            "CreatedAt",
            "PositivePrompt",
            "NegativePrompt",
            "Steps",
            "Sampler",
            "CFGScale",
            "Seed",
            "ImageSize",
            "ModelHash",
            "Model",
            "SeedResizeFrom",
            "DenoisingStrength",
            "Version",
            "NSFWProbability",
            "MD5",
            "SHA1",
            "SHA256",
        ]

        # Create a MySQL database and table if it doesn't exist
        conn = connect_database(host, user, password, database_name, info_logger)

        # Update the database table and columns
        update_database_table(conn, table_name, columns, info_logger)

        # Update the database columns
        update_database_columns(conn, table_name, columns, info_logger)

        inserted_count = 0
        updated_count = 0
        # Loop through the images in the folder
        for root, dirs, files in os.walk(image_folder):  # Do not delete "dirs"!!!
            for filename in files:
                if filename.endswith(".png"):
                    image_path = os.path.join(root, filename)
                    debug_logger.debug(f"Found image file: {image_path}")
                    metadata = get_image_metadata(image_path, info_logger)
                    debug_logger.debug(f"Got metadata from image file: {image_path}")

                    # Extract metadata from parameter
                    extracted_metadata = extract_metadata_from_parameter(
                        metadata,
                        image_path,
                        nsfw,
                        info_logger,
                        debug_logger,
                    )

                    debug_logger.info(
                        f"Extracted metadata from {image_path} is {extracted_metadata}"
                    )

                    # Check if metadata already exists in database
                    row_count = check_if_metadata_exists(
                        conn, extracted_metadata, table_name, debug_logger
                    )

                    debug_logger.info(
                        f"Metadata already exists {row_count} times in database"
                    )

                    if row_count == 0:
                        # Insert metadata into database
                        insert_metadata_into_database(
                            conn,
                            extracted_metadata,
                            table_name,
                            columns,
                            info_logger,
                            extraction_logger,
                        )
                        inserted_count += 1
                    elif row_count == 1:
                        # Check if metadata in database is the same as the extracted metadata
                        equal = check_if_metadata_equal(
                            conn,
                            metadata,
                            table_name,
                            columns,
                            info_logger,
                            debug_logger,
                        )

                        # Update metadata in database
                        if equal == False:
                            update_metadata_in_database(
                                conn,
                                extracted_metadata,
                                table_name,
                                columns,
                                info_logger,
                                extraction_logger,
                            )
                            updated_count += 1
                        else:
                            debug_logger.debug(
                                f"Metadata in database is the same as the extracted metadata."
                            )
                    else:
                        info_logger.error(f"Row count is {row_count}. Expected 0 or 1.")

        # Close the database connection
        conn.close()
        total_count = str(inserted_count + updated_count)
        end_time = datetime.now()
        time_difference = str(end_time - start_time)
        info_logger.info(
            f"Script finished. Duration: {time_difference}, Total count: {total_count} ({str(inserted_count)} inserted, {str(updated_count)} updated)."
        )
    except Exception as e:
        info_logger.error("An unexpected error occurred: %s", str(e))


if __name__ == "__main__":
    start_metadata_extractor()
