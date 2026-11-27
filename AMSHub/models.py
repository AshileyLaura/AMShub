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

    foto = models.ImageField(
        upload_to='perfis/fotos/',
        blank=True
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

    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mentorias'
    )

    tema = models.CharField(max_length=200)
    descricao = models.TextField()
    data = models.DateField()
    carga_horaria = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    area = models.CharField(max_length=100, blank=True, default='')
    horario = models.TimeField(null=True, blank=True)
    vagas = models.PositiveIntegerField(null=True, blank=True)
    modalidade = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return self.tema


class Aluno(models.Model):
    SERIE_CHOICES = [
        ('1', '1º Série'),
        ('2', '2º Série'),
        ('3', '3º Série'),
    ]

    TURMA_CHOICES = [
        ('A', 'Turma A'),
        ('B', 'Turma B'),
    ]

    id_aluno = models.AutoField(primary_key=True)

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name='aluno'
    )

    rm = models.CharField(max_length=50, blank=True, null=True, unique=True)

    curso = models.CharField(
        max_length=200,
        default="Não informado",
        verbose_name="Área/Curso"
    )

    serie = models.CharField(
        max_length=1,
        choices=SERIE_CHOICES,
        default='1',
        verbose_name="Módulo/Série"
    )

    turma = models.CharField(
        max_length=1,
        choices=TURMA_CHOICES,
        default='A',
        verbose_name="Turma"
    )

    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alunos'
    )

    def __str__(self):
        return f"{self.rm or self.id_aluno} - {self.perfil.user.username}"


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

    id_mentoria = models.ForeignKey(
        Mentoria,
        on_delete=models.CASCADE,
        related_name='atividades',
        null=True,
        blank=True
    )

    titulo = models.CharField(max_length=200)
    descricao = models.TextField(default='')
    data_entrega = models.DateField(
        null=True,
        blank=True
    )

    horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=50,
        default='Pendente'
    )

    prioridade = models.CharField(
        max_length=10,
        default='Média'
    )

    def __str__(self):
        return self.titulo


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

    arquivo = models.FileField(
        upload_to='certificados/documentos/',
        blank=True,
        null=True
    )

    link = models.URLField(
        max_length=1000,
        blank=True,
        default=''
    )

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
    descricao = models.TextField()
    requisitos = models.CharField(max_length=500, blank=True)
    data_limite = models.DateField()

    tipo = models.CharField(max_length=30, blank=True, default='')
    modalidade = models.CharField(max_length=20, blank=True, default='')
    localizacao = models.CharField(max_length=150, blank=True, default='')
    quantidade = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return str(self.id_vaga)

class Candidatura(models.Model):
    id_candidatura = models.AutoField(primary_key=True)
    id_aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='candidaturas')
    id_vaga = models.ForeignKey(Vaga, on_delete=models.CASCADE, related_name='candidaturas')
    data_candidatura = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Enviada')

    class Meta:
        unique_together = ('id_aluno', 'id_vaga')
        ordering = ['-data_candidatura']

    def __str__(self):
        return f'{self.id_aluno} -> {self.id_vaga.cargo}'


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


class EntregaPortfolio(models.Model):

    ANOS = [
        (1, '1º Ano'),
        (2, '2º Ano'),
        (3, '3º Ano'),
    ]

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='entregas_portfolio'
    )

    id_mentoria = models.ForeignKey(
        Mentoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_portfolio'
    )

    titulo = models.CharField(max_length=200)

    ano = models.PositiveSmallIntegerField(
        choices=ANOS
    )

    descricao = models.TextField(blank=True)

    link = models.URLField(
        max_length=1000,
        blank=True
    )

    arquivo = models.FileField(
        upload_to='portfolios/pdfs/',
        blank=True
    )

    data_envio = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        default='Pendente'
    )

    nota = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True
    )

    feedback = models.TextField(blank=True)

    data_avaliacao = models.DateTimeField(
        null=True,
        blank=True
    )

    avaliador = models.ForeignKey(
        Professor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_avaliadas'
    )

    class Meta:
        ordering = ['-data_envio']

    def __str__(self):
        return f'{self.titulo} - {self.id_aluno_id}'


class EntregaAtividade(models.Model):
    id_entrega = models.AutoField(primary_key=True)

    id_aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='entregas_atividade'
    )

    id_atividade = models.ForeignKey(
        Atividade,
        on_delete=models.CASCADE,
        related_name='entregas'
    )

    texto_resposta = models.TextField(
        blank=True,
        default=''
    )

    link = models.URLField(
        max_length=1000,
        blank=True,
        default=''
    )

    arquivo = models.FileField(
        upload_to='atividades/entregas/',
        blank=True,
        null=True
    )

    data_envio = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-data_envio']

    def __str__(self):
        return f'Entrega {self.id_atividade.titulo} - {self.id_aluno.perfil.user.username}'

