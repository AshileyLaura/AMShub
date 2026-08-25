from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Perfil(models.Model):

    TIPOS = [
        ('aluno', 'Aluno'),
        ('professor', 'Professor'),
        ('coordenador', 'Coordenador'),
        ('supervisor', 'Supervisor'),
        ('empresa', 'Empresa'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    def __str__(self):
        return f'{self.user.username} - {self.tipo}'




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



class Aluno(models.Model):
    id_aluno = models.AutoField(primary_key=True)

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name='aluno'
    )

    curso = models.CharField(
        max_length=200,
        default="Não informado"
    )

    turma = models.CharField(max_length=200)

    def __str__(self):
        return str(self.id_aluno)


class Professor(models.Model):
    id_professor = models.AutoField(primary_key=True)

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name='professor'
    )

    def __str__(self):
        return str(self.id_professor)


class Supervisor(models.Model):
    id_supervisor = models.AutoField(primary_key=True)

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name='supervisor'
    )

    def __str__(self):
        return str(self.id_supervisor)


class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True)

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name='empresa'
    )

    nome = models.CharField(max_length=200)

    def __str__(self):
        return str(self.id_empresa)


class Atividade(models.Model):
    id_atividade = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id_atividade)


class Participacao(models.Model):
    id_participacao = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    id_mentoria = models.ForeignKey(
        Mentoria,
        on_delete=models.CASCADE
    )

    horas = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    presenca = models.BooleanField()

    def __str__(self):
        return str(self.id_participacao)


class Portfolio(models.Model):
    id_portfolio = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    id_mentoria = models.ForeignKey(
        Mentoria,
        on_delete=models.CASCADE
    )

    resumo = models.TextField()
    aprendizados = models.TextField()
    avaliacao = models.IntegerField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return str(self.id_portfolio)


class Certificado(models.Model):
    id_certificado = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    curso = models.CharField(max_length=200)
    instituicao = models.CharField(max_length=200)
    carga_horaria = models.IntegerField()
    status = models.CharField(max_length=200)

    def __str__(self):
        return str(self.id_certificado)


class Viagem(models.Model):
    id_viagem = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE
    )

    data = models.DateField()
    descricao = models.CharField(max_length=200)

    horas = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    def __str__(self):
        return str(self.id_viagem)


class Vaga(models.Model):
    id_vaga = models.AutoField(primary_key=True)

    id_empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE
    )

    cargo = models.CharField(max_length=200)
    descricao = models.CharField(max_length=200)
    requisitos = models.CharField(max_length=500)
    data_limite = models.DateField()

    def __str__(self):
        return str(self.id_vaga)


class Horas(models.Model):
    id_horas = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    tipo = models.CharField(max_length=200)

    quantidade = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    def __str__(self):
        return str(self.id_horas)


class Notificacao(models.Model):
    id_notificacao = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    mensagem = models.CharField(max_length=200)
    data = models.DateField()
    lida = models.BooleanField()

    def __str__(self):
        return str(self.id_notificacao)
