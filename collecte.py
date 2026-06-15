#!/usr/bin/env python3
# ============================================================
#  SAE2.04 - Script de collecte des donnees capteurs  (OPTION 2)
# ------------------------------------------------------------
#  Recoit les trames MQTT, les insere DIRECTEMENT dans MySQL avec
#  des requetes SQL brutes, et gere les coupures de la base grace
#  a un cache local (deconnexion / reconnexion).
#
#  Conforme aux validations du sujet (slides 19, 26, 29) :
#    - reception des messages en mode terminal
#    - insertion en base via requetes SQL (INSERT, sans ORM)
#    - gestion deconnexion / reconnexion de la base de donnees
#
#  Dependances :  pip install paho-mqtt PyMySQL
#  Lancement   :  python3 collecte.py     (Ctrl+C pour arreter)
# ============================================================

import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt
import pymysql

# ------------------------- CONFIG ---------------------------
BROKER = "test.mosquitto.org"
PORT = 1883
TOPICS = [
    "IUT/Colmar2026/SAE2.04/Maison1",
    "IUT/Colmar2026/SAE2.04/Maison2",
]

DB = {
    "host": "127.0.0.1",      # 127.0.0.1 si MySQL est local, sinon IP de la VM Windows
    "user": "sae",
    "password": "motdepasse",
    "database": "sae204",
    "connect_timeout": 5,
}

CACHE = "cache.jsonl"          # mesures en attente quand la base est injoignable
_conn = None                   # connexion MySQL reutilisee entre les messages
# ------------------------------------------------------------


# ============================================================
#  1) PARSING DE LA TRAME MQTT
# ============================================================
def parse_message(payload: str) -> dict:
    """
    Transforme la trame en dictionnaire normalise.

    Trame type :
      Id=12A6B8AF6CD3,piece=sejour,date=15/06/2026,heure=12:13:14,temp=26,35

    PIEGE A CONNAITRE POUR L'ORAL : la temperature "26,35" contient une
    virgule, exactement comme le separateur de champs. Un simple split(',')
    la couperait en deux. On recolle le morceau orphelin (le "35") a la
    valeur precedente avec un point decimal.
    """
    brut = {}
    derniere_cle = None
    for morceau in payload.split(","):
        if "=" in morceau:
            cle, valeur = morceau.split("=", 1)
            brut[cle] = valeur
            derniere_cle = cle
        elif derniere_cle is not None:
            brut[derniere_cle] = brut[derniere_cle] + "." + morceau

    # On combine date + heure en un timestamp au format MySQL (AAAA-MM-JJ HH:MM:SS)
    dt = datetime.strptime(f"{brut['date']} {brut['heure']}", "%d/%m/%Y %H:%M:%S")
    return {
        "id": brut["Id"],
        "piece": brut["piece"],
        "date_mesure": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": float(brut["temp"]),
    }


# ============================================================
#  2) ACCES BASE DE DONNEES (requetes SQL brutes, sans ORM)
# ============================================================
def get_connexion():
    """
    Renvoie une connexion MySQL vivante, ou None si la base est injoignable.
    Si la connexion existait mais a expire, ping(reconnect=True) la relance.
    """
    global _conn
    try:
        if _conn is None:
            _conn = pymysql.connect(**DB)
        else:
            _conn.ping(reconnect=True)
        return _conn
    except pymysql.MySQLError:
        _conn = None
        return None


def inserer_mesure(conn, m: dict):
    """Insere une mesure avec deux requetes SQL brutes."""
    with conn.cursor() as cur:
        # 1) Cree le capteur s'il n'existe pas encore.
        #    nom par defaut = id (garantit l'unicite), emplacement = piece.
        #    INSERT IGNORE = ne fait rien si l'id est deja present.
        cur.execute(
            "INSERT IGNORE INTO capteur (id, nom, piece, emplacement) "
            "VALUES (%s, %s, %s, %s)",
            (m["id"], m["id"], m["piece"], m["piece"]),
        )
        # 2) Insere la temperature (cle etrangere capteur_id)
        cur.execute(
            "INSERT INTO mesure (capteur_id, date_mesure, temperature) "
            "VALUES (%s, %s, %s)",
            (m["id"], m["date_mesure"], m["temperature"]),
        )
    conn.commit()


# ============================================================
#  3) CACHE  (gestion deconnexion / reconnexion)
# ============================================================
def mettre_en_cache(m: dict):
    """Base injoignable -> on garde la mesure dans un fichier local."""
    with open(CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps(m) + "\n")
    print(f"  [CACHE] base injoignable, mesure mise de cote ({m['id']})")


def vider_cache(conn):
    """Base revenue -> on rejoue toutes les mesures restees en attente."""
    if not os.path.exists(CACHE):
        return
    with open(CACHE, encoding="utf-8") as f:
        en_attente = [json.loads(ligne) for ligne in f if ligne.strip()]
    if not en_attente:
        return
    for m in en_attente:
        inserer_mesure(conn, m)
    os.remove(CACHE)
    print(f"  [CACHE] {len(en_attente)} mesure(s) re-inseree(s) apres reconnexion")


# ============================================================
#  4) CALLBACKS MQTT
# ============================================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connecte au broker {BROKER}")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"  abonne a {topic}")
    else:
        print(f"Echec de connexion au broker (code {reason_code})")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore").strip()
    try:
        m = parse_message(payload)
    except (KeyError, ValueError) as e:
        print(f"Trame ignoree ({e}) : {payload}")
        return

    # Affichage terminal (exige par les validations, slide 19)
    print(f"Recu  id={m['id']}  piece={m['piece']}  "
          f"{m['date_mesure']}  temp={m['temperature']} C")

    conn = get_connexion()
    if conn is not None:
        try:
            vider_cache(conn)          # on rattrape d'abord ce qui attendait
            inserer_mesure(conn, m)    # puis on insere la mesure courante
            print("  -> insere en base")
        except pymysql.MySQLError as e:
            print(f"  [ERREUR SQL] {e}")
            mettre_en_cache(m)
    else:
        mettre_en_cache(m)


# ============================================================
#  5) BOUCLE PRINCIPALE
# ============================================================
def main():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)  # reconnexion MQTT auto

    print("Demarrage du collecteur... (Ctrl+C pour arreter)")
    client.connect(BROKER, PORT, keepalive=60)

    try:
        client.loop_forever()   # ecoute en continu et se reconnecte tout seul
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
    finally:
        client.disconnect()
        if _conn is not None:
            _conn.close()
        print("Collecteur arrete proprement.")


if __name__ == "__main__":
    main()
