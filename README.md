# SAÉ 2.04 : Tableau de bord des capteurs de température

Application web Django qui affiche les relevés de température collectés par des capteurs domestiques.
Les relevés sont envoyés en MQTT, enregistrés dans MySQL par le service [Collecte](https://github.com/hussainshaqsi/Collecte), puis affichés ici.

```
Capteurs --MQTT--> Collecte (Python) --SQL--> MySQL <--lecture-- Tableau de bord Django (ce dépôt)
```

## Fonctionnalités
- Liste des capteurs (`Capteur`) avec leur pièce et leur emplacement
- Page de détail par capteur avec ses mesures (`Mesure` : date et température)
- Les modèles correspondent à des tables MySQL existantes (`managed = False`) : Django ne modifie jamais le schéma

## Technologies
Python, Django, MySQL, templates HTML/CSS

## Lancer en local

```bash
python -m venv venv && source venv/bin/activate   # Windows : venv\Scripts\activate
pip install django mysqlclient
cp .env.example .env                               # puis exporter les variables, ou les définir dans le terminal
python manage.py runserver
```

La configuration est lue depuis des variables d'environnement (voir `.env.example`) : `DJANGO_SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

## Contexte
Projet universitaire (BUT Réseaux & Télécommunications, IUT de Colmar, semestre 2).
