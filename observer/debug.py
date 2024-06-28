import os
import json

chemin = "../in/toto.json"
with open(chemin,"r") as file:
            fichier = json.load(file)
            print (fichier)