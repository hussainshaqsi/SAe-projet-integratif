from django.db import models

class Capteur(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    nom = models.CharField(max_length=50, unique=True)
    piece = models.CharField(max_length=50)
    emplacement = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "capteur"

    def __str__(self):
        return self.nom


class Mesure(models.Model):
    id = models.AutoField(primary_key=True)
    capteur = models.ForeignKey(Capteur, on_delete=models.CASCADE, db_column="capteur_id")
    date_mesure = models.DateTimeField()
    temperature = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = "mesure"