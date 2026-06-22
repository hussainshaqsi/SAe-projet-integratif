import csv
import json
from django.db.models import Avg, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Capteur, Mesure


# ============================================================
#  FILTRES (partages entre liste, graphe, export CSV)
# ============================================================
def appliquer_filtres(request):
    mesures = Mesure.objects.select_related("capteur").all()

    capteur = request.GET.get("capteur", "").strip()
    if capteur:
        mesures = mesures.filter(
            Q(capteur__id__icontains=capteur)
            | Q(capteur__nom__icontains=capteur)
            | Q(capteur__piece__icontains=capteur)
        )

    date_debut = request.GET.get("date_debut", "").strip()
    if date_debut:
        mesures = mesures.filter(timestamp__date__gte=date_debut)

    date_fin = request.GET.get("date_fin", "").strip()
    if date_fin:
        mesures = mesures.filter(timestamp__date__lte=date_fin)

    temp_min = request.GET.get("temp_min", "").strip()
    if temp_min:
        try:
            mesures = mesures.filter(temperature__gte=float(temp_min))
        except ValueError:
            pass

    temp_max = request.GET.get("temp_max", "").strip()
    if temp_max:
        try:
            mesures = mesures.filter(temperature__lte=float(temp_max))
        except ValueError:
            pass

    tris_valides = {
        "date": "timestamp",
        "temperature": "temperature",
        "capteur": "capteur__id",
        "nom": "capteur__nom",
        "piece": "capteur__piece",
    }
    tri = tris_valides.get(request.GET.get("tri", "date"), "timestamp")
    ordre = "" if request.GET.get("ordre", "desc") == "asc" else "-"
    return mesures.order_by(f"{ordre}{tri}")


def _points_graphe(mesures, max_points=120):
    """Downsample pour eviter la bouillie quand il y a 500+ points."""
    points = list(mesures.order_by("timestamp"))
    n = len(points)
    if n > max_points:
        pas = n // max_points
        points = points[::pas][-max_points:]
    return (
        [p.timestamp.strftime("%d/%m %H:%M") for p in points],
        [float(p.temperature) for p in points],
    )


# ============================================================
#  PAGE PRINCIPALE
# ============================================================
def liste(request):
    mesures = appliquer_filtres(request)
    moyenne = mesures.aggregate(m=Avg("temperature"))["m"]
    labels, valeurs = _points_graphe(mesures)

    try:
        refresh = max(0, int(request.GET.get("refresh", "0")))
    except ValueError:
        refresh = 0

    return render(request, "capteurs/liste.html", {
        "mesures": mesures[:500],
        "total_mesures": mesures.count(),
        "moyenne": moyenne,
        "capteurs": Capteur.objects.all(),
        "labels": json.dumps(labels),
        "valeurs": json.dumps(valeurs),
        "refresh": refresh,
        "f_capteur": request.GET.get("capteur", ""),
        "f_debut": request.GET.get("date_debut", ""),
        "f_fin": request.GET.get("date_fin", ""),
        "f_tmin": request.GET.get("temp_min", ""),
        "f_tmax": request.GET.get("temp_max", ""),
        "tri": request.GET.get("tri", "date"),
        "ordre": request.GET.get("ordre", "desc"),
    })


# ============================================================
#  PAGE D'UN CAPTEUR : edition (nom + emplacement) et suppression
# ============================================================
def detail(request, capteur_id):
    capteur = get_object_or_404(Capteur, id=capteur_id)

    if request.method == "POST":
        if "supprimer" in request.POST:
            capteur.delete()  # CASCADE supprime aussi ses mesures
            return redirect("liste")

        nouveau_nom = request.POST.get("nom", "").strip()
        nouvel_emplacement = request.POST.get("emplacement", "").strip()
        if nouveau_nom:
            capteur.nom = nouveau_nom
        if nouvel_emplacement:
            capteur.emplacement = nouvel_emplacement
        # id et piece ne sont jamais touches
        capteur.save(update_fields=["nom", "emplacement"])
        return redirect("detail", capteur_id=capteur.id)

    mesures = Mesure.objects.filter(capteur=capteur).order_by("-timestamp")
    moyenne = mesures.aggregate(m=Avg("temperature"))["m"]
    labels, valeurs = _points_graphe(mesures)

    return render(request, "capteurs/detail.html", {
        "capteur": capteur,
        "mesures": mesures[:500],
        "total_mesures": mesures.count(),
        "moyenne": moyenne,
        "labels": json.dumps(labels),
        "valeurs": json.dumps(valeurs),
    })


# ============================================================
#  EXPORT CSV (respecte les filtres actifs)
# ============================================================
def export_csv(request):
    mesures = appliquer_filtres(request)
    reponse = HttpResponse(content_type="text/csv")
    reponse["Content-Disposition"] = 'attachment; filename="mesures.csv"'
    writer = csv.writer(reponse)
    writer.writerow(["capteur_id", "nom", "piece", "timestamp", "temperature"])
    for m in mesures:
        writer.writerow([
            m.capteur_id, m.capteur.nom, m.capteur.piece,
            m.timestamp, m.temperature,
        ])
    return reponse