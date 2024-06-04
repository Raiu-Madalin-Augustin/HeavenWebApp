from flask import Flask, request, jsonify, send_from_directory
from azure.data.tables import TableServiceClient, TableEntity
from azure.storage.blob import BlobServiceClient, BlobClient
import os
from werkzeug.utils import secure_filename
import datetime

app = Flask(__name__)

# Configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("DefaultEndpointsProtocol=https;AccountName=heavenstorage;AccountKey=CgnCARmiqsCQ/4WcoF/JR9Vvs+rabrtjCqnj1e+xCmMijWRgA3es34XvgU30gcReFIKm9iesBpeZ+ASt2V3zRQ==;EndpointSuffix=core.windows.net")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("heavenstorage")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("CgnCARmiqsCQ/4WcoF/JR9Vvs+rabrtjCqnj1e+xCmMijWRgA3es34XvgU30gcReFIKm9iesBpeZ+ASt2V3zRQ==")
TABLE_NAME = "Recipes"
BLOB_CONTAINER_NAME = "original-images"
RESIZED_BLOB_CONTAINER_NAME = "resized-images"

# Initialize Azure clients
table_service_client = TableServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
table_client = table_service_client.get_table_client(table_name=TABLE_NAME)

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
resized_blob_container_client = blob_service_client.get_container_client(RESIZED_BLOB_CONTAINER_NAME)

# Ensure containers exist
blob_container_client.create_container()
resized_blob_container_client.create_container()

# Directory to serve static files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    title = request.form['title']
    ingredients = request.form['ingredients']
    steps = request.form['steps']
    image = request.files['image']

    recipe_id = str(int(datetime.datetime.now().timestamp()))
    partition_key = "RecipePartition"
    row_key = recipe_id

    # Secure the filename and save the image to blob storage
    filename = secure_filename(image.filename)
    blob_name = f"{recipe_id}-{filename}"
    blob_client = blob_container_client.get_blob_client(blob_name)
    blob_client.upload_blob(image)

    # Create a table entity
    entity = TableEntity(
        PartitionKey=partition_key,
        RowKey=row_key,
        Title=title,
        Ingredients=ingredients,
        Steps=steps,
        ImageURL=blob_client.url,
        Timestamp=datetime.datetime.utcnow().isoformat()
    )

    table_client.create_entity(entity)

    return jsonify({"message": "Recipe created successfully"}), 201

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    query = table_client.list_entities()
    recipes = []
    for entity in query:
        recipes.append({
            "RecipeID": entity['RowKey'],
            "Title": entity['Title'],
            "Ingredients": entity['Ingredients'],
            "Steps": entity['Steps'],
            "ImageURL": entity['ImageURL'],
            "Timestamp": entity['Timestamp']
        })

    recipes.sort(key=lambda x: x['Timestamp'], reverse=True)
    return jsonify(recipes)


if __name__ == '__main__':
    app.run(debug=True)
