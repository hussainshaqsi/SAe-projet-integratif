# SAÉ 2.04: Temperature sensor dashboard

Django web app that displays the temperature readings collected from home sensors.
Readings are pushed over MQTT, stored in MySQL by the [Collecte](https://github.com/hussainshaqsi/Collecte) service, and shown here.

```
Sensors --MQTT--> Collecte (Python) --SQL--> MySQL <--read-- Django dashboard (this repo)
```

## Features
- List of sensors (`Capteur`) with their room and location
- Detail page per sensor with its measurements (`Mesure`: timestamp and temperature)
- Models map to existing MySQL tables (`managed = False`), so Django never alters the schema

## Stack
Python, Django, MySQL, HTML/CSS templates

## Run locally

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install django mysqlclient
cp .env.example .env                               # then export the variables, or set them in your shell
python manage.py runserver
```

Configuration is read from environment variables (see `.env.example`): `DJANGO_SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

## Context
University project (BUT Réseaux & Télécommunications, IUT de Colmar, semester 2).
