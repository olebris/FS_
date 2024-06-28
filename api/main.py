from fastapi import FastAPI
from minio import Minio
from fastapi.responses import StreamingResponse
import io
from fastapi.responses import JSONResponse
import redis
import json

app = FastAPI()

# Configuration MinIO
minio_client = Minio(
    "minio:9000",
    access_key="yWyHyc1OxMagrdkJVsfC",
    secret_key="oyBpR3x987VieQ4MbeR0aqD2DmMWCATGIHWIJgFz",
    secure=False  # Passer à True si vous utilisez HTTPS
)
# Configuration Redis
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

def clean_newlines(json_content):
    # Supprimer les caractères de nouvelle ligne du contenu JSON
    return json_content.replace("\n", "")

# API fichiers

@app.get("/get_file_minio_json/{file_name}")
async def get_file_minio_json(file_name: str):
    try:
        # Récupérer l'objet MinIO
        obj = minio_client.get_object("mfi-test", file_name)

        # Lire le contenu du fichier en tant que chaîne JSON
        json_content = obj.read().decode("utf-8")

        # Charger la chaîne en JSON 
        data = json.loads(json_content)

        # Retourner le JSON
        return JSONResponse(content=data, media_type="application/json")
    except Exception as e:
        return {"error": f"File {file_name} not found - {e}"}


@app.get("/get_redis_geojson")
async def get_redis_geojson(layer: str = None, date: int = None):
    try:
        # Construire la clé pour la recherche dans Redis en fonction des filtres
        key = "latest"

        if layer:
            key = f"hget {key} {layer}"
        elif date:
            key = f"hget {key} {layer}"
        else:
            key = f"hget {key} all"
        print (key)

        # Récupérer les éléments depuis Redis
        result = redis_client.execute_command(key)
        print(f"Results from Redis: {result}")

               
        feature = json.loads(result.decode("utf-8"))
        
        
        
        return JSONResponse(content=feature)

    except Exception as e:
        return JSONResponse(content={"error": f"An error occurred: {str(e)}"}, status_code=500)
