import csv
import json
from django.db.models import Avg, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Capteur, Mesure


def appliquer_filtres(request):
    """Filtre les mesures selon l'URL : ?capteur=... &date_debut=... &date_fin=..."""
    mesures = Mesure.objects.select_related("capteur").all()

    capteur = request.GET.get("capteur", "").strip()
    if capteur:
        mesures = mesures.filter(Q(capteur__id=capteur) | Q(capteur__nom__icontains=capteur))

    date_debut = request.GET.get("date_debut", "").strip()
    if date_debut:
        mesures = mesures.filter(date_mesure__date__gte=date_debut)

    date_fin = request.GET.get("date_fin", "").strip()
    if date_fin:
        mesures = mesures.filter(date_mesure__date__lte=date_fin)

    return mesures.order_by("-date_mesure")


def liste(request):
    mesures = appliquer_filtres(request)
    moyenne = mesures.aggregate(m=Avg("temperature"))["m"]

    # données pour le graphique (100 dernières, ordre chronologique)
    points = list(mesures.order_by("date_mesure")[:100])
    labels = [p.date_mesure.strftime("%d/%m %H:%M") for p in points]
    temperatures = [float(p.temperature) for p in points]

    contexte = {
        "mesures": mesures[:500],
        "moyenne": moyenne,
        "labels_json": json.dumps(labels),
        "temps_json": json.dumps(temperatures),
        "f_capteur": request.GET.get("capteur", ""),
        "f_debut": request.GET.get("date_debut", ""),
        "f_fin": request.GET.get("date_fin", ""),
        "refresh": request.GET.get("refresh", ""),
    }
    return render(request, "capteurs/liste.html", contexte)


def detail(request, capteur_id):
    capteur = get_object_or_404(Capteur, id=capteur_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "modifier":
            # seuls nom et emplacement sont modifiables
            capteur.nom = request.POST.get("nom", capteur.nom)
            capteur.emplacement = request.POST.get("emplacement", capteur.emplacement)
            capteur.save()
            return redirect("detail", capteur_id=capteur.id)
        if action == "supprimer":
            capteur.delete()  # cascade -> supprime aussi les mesures
            return redirect("liste")

    mesures = Mesure.objects.filter(capteur=capteur).order_by("-date_mesure")[:500]
    moyenne = Mesure.objects.filter(capteur=capteur).aggregate(m=Avg("temperature"))["m"]
    return render(request, "capteurs/detail.html",
                  {"capteur": capteur, "mesures": mesures, "moyenne": moyenne})


def export_csv(request):
    mesures = appliquer_filtres(request)
    reponse = HttpResponse(content_type="text/csv")
    reponse["Content-Disposition"] = 'attachment; filename="mesures.csv"'
    writer = csv.writer(reponse)
    writer.writerow(["capteur_id", "nom", "date_mesure", "temperature"])
    for m in mesures:
        writer.writerow([m.capteur.id, m.capteur.nom, m.date_mesure, m.temperature])
    return reponse