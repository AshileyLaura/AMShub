from django.db import models

# Create your models here.

# mentoria

class Mentoria(models.Model):
    id_mentoria = models.AutoField(primary_key=True)

    id_professor = models.ForeignKey(
        'Professor',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    id_supervisor = models.ForeignKey(
        'Supervisor',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    tema = models.CharField(max_length=200)
    descricao = models.TextField()
    data = models.DateField()
    carga_horaria = models.IntegerField()

    def __str__(self):
        return self.tema


# usuario

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_usuario)



# aluno

class Aluno(models.Model):
    id_aluno = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_aluno)



# professor

class Professor(models.Model):
    id_professor = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_professor)



# supervisor

class Supervisor(models.Model):
    id_supervisor = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_supervisor)



# empersas

class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_empresa)


# atividade

class Atividade(models.Model):
    id_atividade = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_atividade)



# participacao

class Participacao(models.Model):
    id_participacao = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_participacao)


# portifolio

class Portfolio(models.Model):
    id_portfolio = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_portfolio)


# certificado

class Certificado(models.Model):
    id_certificado = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_certificado)


# viagem

class Viagem(models.Model):
    id_viagem = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_viagem)


# vaga

class Vaga(models.Model):
    id_vaga = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_vaga)


# horas

class Horas(models.Model):
    id_horas = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_horas)


# notificacao
class Notificacao(models.Model):
    id_notificacao = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_notificacao)