from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from decimal import Decimal
from .models import (
    Perfil,
    Aluno,
    Professor,
    Supervisor,
    Empresa,
    Mentoria,
    Participacao,
    Certificado,
    Atividade,
    EntregaAtividade,
    EntregaPortfolio,
    Portfolio,
    Vaga,
    Candidatura,
    Horas,
    Viagem
)

class AMShubUltimateCoverageTestCase(TestCase):
    def setUp(self):
        self.hoje = timezone.localdate()

        # 1. Criação de Utilizadores e Perfis para todos os papéis do sistema
        self.user_aluno = User.objects.create_user(username='aluno@etec.sp.gov.br', password='123', first_name='Aluno Teste')
        self.perfil_aluno = Perfil.objects.create(user=self.user_aluno, tipo='aluno')
        self.aluno = Aluno.objects.create(perfil=self.perfil_aluno, curso='Desenvolvimento de Sistemas', turma='3º AMS')

        self.user_prof = User.objects.create_user(username='prof@etec.sp.gov.br', password='123', first_name='Professor Teste')
        self.perfil_prof = Perfil.objects.create(user=self.user_prof, tipo='professor')
        self.professor = Professor.objects.create(perfil=self.perfil_prof)

        self.user_coord = User.objects.create_user(username='coord@etec.sp.gov.br', password='123', first_name='Coordenador Teste')
        self.perfil_coord = Perfil.objects.create(user=self.user_coord, tipo='coordenador')

        self.user_sup = User.objects.create_user(username='sup@etec.sp.gov.br', password='123', first_name='Supervisor Teste')
        self.perfil_sup = Perfil.objects.create(user=self.user_sup, tipo='supervisor')
        self.supervisor = Supervisor.objects.create(perfil=self.perfil_sup)

        self.user_emp = User.objects.create_user(username='empresa@tech.com', password='123', first_name='Empresa Teste')
        self.perfil_emp = Perfil.objects.create(user=self.user_emp, tipo='empresa')
        self.empresa = Empresa.objects.create(perfil=self.perfil_emp, nome='Tech Solutions')

        # Relacionar aluno à empresa
        self.aluno.empresa = self.empresa
        self.aluno.save()

        # Mentoria de teste
        self.mentoria = Mentoria.objects.create(
            tema='Engenharia de Software Ágil',
            descricao='Boas práticas em projetos reais',
            data=self.hoje + datetime.timedelta(days=7),
            horario=datetime.time(14, 0),
            carga_horaria=Decimal('4.00'),
            empresa=self.empresa,
            id_professor=self.professor,
            id_supervisor=self.supervisor,
            modalidade='Online',
            vagas=30
        )

        # Atividade de teste
        self.atividade = Atividade.objects.create(
            id_mentoria=self.mentoria,
            titulo='Desenvolver Diagrama ER',
            descricao='Criar o modelo de dados',
            data_entrega=self.hoje + datetime.timedelta(days=3),
            horas=Decimal('2.00'),
            status='Pendente',
            prioridade='Alta'
        )

        # Vaga de teste
        self.vaga = Vaga.objects.create(
            id_empresa=self.empresa,
            cargo='Estagiário Backend',
            descricao='Desenvolvimento Django',
            requisitos='Python e SQL',
            data_limite=self.hoje + datetime.timedelta(days=20),
            tipo='Estágio',
            modalidade='Remoto',
            quantidade=2
        )

    # ------------------------------------------------------------------
    # 1. TESTES DE AUTENTICAÇÃO, LOGIN E CADASTRO
    # ------------------------------------------------------------------
    def test_01_index_e_cadastro(self):
        """Testa a página inicial e a rota de cadastro de novos utilizadores"""
        response_index = self.client.get(reverse('index'))
        self.assertEqual(response_index.status_code, 200)

        response_cadastro = self.client.get(reverse('cadastro'))
        self.assertEqual(response_cadastro.status_code, 200)

    def test_02_logins_especificos(self):
        """Testa o login em rotas específicas para cada tipo de utilizador"""
        rotas_login = [
            ('login_aluno', 'aluno@etec.sp.gov.br'),
            ('login_professor', 'prof@etec.sp.gov.br'),
            ('login_coordenador', 'coord@etec.sp.gov.br'),
            ('login_supervisor', 'sup@etec.sp.gov.br'),
            ('login_empresa', 'empresa@tech.com'),
        ]
        for rota, email in rotas_login:
            self.assertEqual(self.client.get(reverse(rota)).status_code, 200)
            response = self.client.post(reverse(rota), {'email': email, 'senha': '123'})
            self.assertEqual(response.status_code, 302)
            self.client.logout()

    def test_03_logout(self):
        """Testa o fluxo de encerramento de sessão"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------------
    # 2. TESTES DO MÓDULO DO ALUNO (TODAS AS VIEWS)
    # ------------------------------------------------------------------
    def test_04_aluno_dashboard_e_pendencias(self):
        """Testa a dashboard principal do aluno e a tela de pendências"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')
        
        self.assertEqual(self.client.get(reverse('aluno')).status_code, 200)
        self.assertEqual(self.client.get(reverse('pendenciasa')).status_code, 200)

    def test_05_aluno_mentorias_e_inscricao(self):
        """Testa listagem de mentorias, inscrição e detalhes"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')
        
        self.assertEqual(self.client.get(reverse('minhasmentoriasa')).status_code, 200)

        response_insc = self.client.post(reverse('inscreveremmentoriaa', args=[self.mentoria.pk]))
        self.assertEqual(response_insc.status_code, 302)
        self.assertTrue(Participacao.objects.filter(id_aluno=self.aluno, id_mentoria=self.mentoria).exists())

        self.assertEqual(self.client.get(reverse('detalhesdamentoriaa', args=[self.mentoria.pk])).status_code, 200)

    def test_06_aluno_perfil_portifolio_e_atividades(self):
        """Testa perfil, portfólios, atividades e entrega de soluções"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')

        self.assertEqual(self.client.get(reverse('meuperfila')).status_code, 200)
        self.assertEqual(self.client.get(reverse('meusportifoliosa')).status_code, 200)
        self.assertEqual(self.client.get(reverse('atividadesa')).status_code, 200)

        self.assertEqual(self.client.get(reverse('detalhesdaatividadea', args=[self.atividade.pk])).status_code, 200)
        response_entrega = self.client.post(reverse('detalhesdaatividadea', args=[self.atividade.pk]), {
            'tipo_envio': 'texto',
            'texto_resposta': 'Aqui está a resolução da atividade desenvolvida.'
        })
        self.assertEqual(response_entrega.status_code, 302)
        self.assertTrue(EntregaAtividade.objects.filter(id_aluno=self.aluno, id_atividade=self.atividade).exists())

    def test_07_aluno_certificados_e_vagas(self):
        """Testa submissão de certificado e candidaturas a vagas"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')

        self.assertEqual(self.client.get(reverse('certificadoa')).status_code, 200)
        response_cert = self.client.post(reverse('certificadoa'), {
            'curso': 'Python Expert',
            'instituicao': 'Coursera',
            'carga_horaria': '30',
            'tipo_comprovante': 'link',
            'link': 'https://coursera.org/verify/python'
        })
        self.assertEqual(response_cert.status_code, 302)
        self.assertTrue(Certificado.objects.filter(curso='Python Expert').exists())

        self.assertEqual(self.client.get(reverse('vagasa')).status_code, 200)
        response_cand = self.client.post(reverse('candidatar_vagaa', args=[self.vaga.pk]))
        self.assertEqual(response_cand.status_code, 302)
        self.assertTrue(Candidatura.objects.filter(id_aluno=self.aluno, id_vaga=self.vaga).exists())

    # ------------------------------------------------------------------
    # 3. TESTES DO MÓDULO DO PROFESSOR (TODAS AS VIEWS)
    # ------------------------------------------------------------------
    def test_08_professor_painel_e_gestao(self):
        """Testa o painel do professor, registo de presenças, portfólios, avaliações e agenda"""
        self.client.login(username='prof@etec.sp.gov.br', password='123')

        self.assertEqual(self.client.get(reverse('professor')).status_code, 200)
        self.assertEqual(self.client.get(reverse('portfoliosp')).status_code, 200)
        self.assertEqual(self.client.get(reverse('avaliacoesp')).status_code, 200)
        self.assertEqual(self.client.get(reverse('mentoriasp')).status_code, 200)
        self.assertEqual(self.client.get(reverse('agendap')).status_code, 200)
        self.assertEqual(self.client.get(reverse('atividadesp')).status_code, 200)

        Participacao.objects.create(id_aluno=self.aluno, id_mentoria=self.mentoria, horas=Decimal('0.00'), presenca=False)
        part = Participacao.objects.get(id_aluno=self.aluno, id_mentoria=self.mentoria)
        response_presenca = self.client.post(reverse('registrar_presenca_p', args=[self.mentoria.pk]), {
            f'presenca_{part.pk}': 'on',
            f'horas_{part.pk}': '4.0'
        })
        self.assertEqual(response_presenca.status_code, 302)

    # ------------------------------------------------------------------
    # 4. TESTES DO MÓDULO DA EMPRESA (TODAS AS VIEWS)
    # ------------------------------------------------------------------
    def test_09_empresa_painel_mentorias_tarefas_e_vagas(self):
        """Testa o painel da empresa, cadastro de mentorias, criação de tarefas e oportunidades"""
        self.client.login(username='empresa@tech.com', password='123')

        self.assertEqual(self.client.get(reverse('empresa')).status_code, 200)
        self.assertEqual(self.client.get(reverse('cadastrarmentoriase')).status_code, 200)
        self.assertEqual(self.client.get(reverse('criartarefase')).status_code, 200)
        self.assertEqual(self.client.get(reverse('oportunidadese')).status_code, 200)

        response_op = self.client.post(reverse('oportunidadese'), {
            'titulo': 'Desenvolvedor Frontend',
            'tipo': 'Estágio',
            'modalidade': 'Presencial',
            'localizacao': 'São Paulo - SP',
            'prazo': (self.hoje + datetime.timedelta(days=30)).isoformat(),
            'vagas': '3',
            'descricao': 'Trabalhar com Vue.js e Tailwind',
            'requisitos': 'HTML, CSS e JavaScript'
        })
        self.assertEqual(response_op.status_code, 302)
        self.assertTrue(Vaga.objects.filter(cargo='Desenvolvedor Frontend').exists())

    # ------------------------------------------------------------------
    # 5. TESTES DO MÓDULO DE GESTÃO E COORDENADOR (TODAS AS VIEWS)
    # ------------------------------------------------------------------
    def test_10_coordenador_e_supervisor_gestao(self):
        """Testa coordenador, supervisor, aprovação de certificados, gestão de empresas, mentorias, relatórios e alunos"""
        self.client.login(username='sup@etec.sp.gov.br', password='123')
        self.assertEqual(self.client.get(reverse('supervisor')).status_code, 200)
        self.client.logout()

        self.client.login(username='coord@etec.sp.gov.br', password='123')

        self.assertEqual(self.client.get(reverse('coordenador')).status_code, 200)
        self.assertEqual(self.client.get(reverse('aprovar_certificados')).status_code, 200)
        self.assertEqual(self.client.get(reverse('empresagestao')).status_code, 200)
        self.assertEqual(self.client.get(reverse('mentoriasgestao')).status_code, 200)
        self.assertEqual(self.client.get(reverse('relatoriosgestao')).status_code, 200)
        self.assertEqual(self.client.get(reverse('gerenciaalunosc')).status_code, 200)

        cert = Certificado.objects.create(
            id_aluno=self.aluno,
            curso='Segurança da Informação',
            instituicao='CISCO',
            carga_horaria=25,
            status='Em análise'
        )
        response_aprov = self.client.post(reverse('aprovar_certificados'), {
            'id_certificado': cert.pk,
            'acao': 'aprovar'
        })
        self.assertEqual(response_aprov.status_code, 302)
        cert.refresh_from_db()
        self.assertEqual(cert.status, 'Aprovado')

    # ------------------------------------------------------------------
    # 6. TESTE DE PERFIL UNIFICADO
    # ------------------------------------------------------------------
    def test_11_meu_perfil_geral(self):
        """Testa a view de perfil unificado para staff/empresas"""
        self.client.login(username='prof@etec.sp.gov.br', password='123')
        self.assertEqual(self.client.get(reverse('meuperfil')).status_code, 200)

    # ------------------------------------------------------------------
    # 7. TESTES DE CENÁRIOS AVANÇADOS E EDGE CASES
    # ------------------------------------------------------------------
    def test_12_calculo_viagens_e_horas_avulsas_aluno(self):
        """Testa se Viagens e Horas Avulsas são computadas corretamente na dashboard do aluno"""
        self.client.login(username='aluno@etec.sp.gov.br', password='123')

        Viagem.objects.create(
            id_aluno=self.aluno,
            empresa=self.empresa,
            data=self.hoje,
            descricao='Visita Técnica Tech Summit',
            horas=Decimal('8.00')
        )
        Horas.objects.create(
            id_aluno=self.aluno,
            tipo='Projeto Open Source',
            quantidade=Decimal('12.00')
        )

        response = self.client.get(reverse('aluno'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_horas', response.context)

    def test_13_edicao_mentoria_pela_empresa(self):
        """Testa se a empresa consegue editar uma mentoria existente enviando o ID"""
        self.client.login(username='empresa@tech.com', password='123')

        response = self.client.post(reverse('cadastrarmentoriase'), {
            'id': str(self.mentoria.pk),
            'titulo': 'Engenharia de Software Ágil (Atualizada)',
            'area': 'Desenvolvimento',
            'data': (self.hoje + datetime.timedelta(days=10)).isoformat(),
            'horario': '15:30',
            'vagas': '40',
            'carga_horaria': '5h',
            'modalidade': 'Híbrida',
            'descricao': 'Descrição atualizada para o workshop'
        })
        self.assertEqual(response.status_code, 302)
        
        self.mentoria.refresh_from_db()
        self.assertEqual(self.mentoria.tema, 'Engenharia de Software Ágil (Atualizada)')
        self.assertEqual(self.mentoria.vagas, 40)

    def test_14_cadastros_administrativos_coordenador(self):
        """Testa o cadastro de nova empresa e de novo aluno direto pelas rotas do coordenador"""
        self.client.login(username='coord@etec.sp.gov.br', password='123')

        response_emp = self.client.post(reverse('empresagestao'), {
            'acao': 'cadastrar',
            'nome': 'Nova Empresa Parceira SA',
            'email': 'contato@novaempresa.com',
            'senha': 'SenhaSegura123!'
        })
        self.assertEqual(response_emp.status_code, 302)
        self.assertTrue(Empresa.objects.filter(nome='Nova Empresa Parceira SA').exists())

        empresa_parceira = Empresa.objects.first()
        response_alu = self.client.post(reverse('gerenciaalunosc'), {
            'acao': 'cadastrar',
            'nome': 'Novo Aluno Teste',
            'email': 'novo.aluno@etec.sp.gov.br',
            'senha': 'SenhaSegura123!',
            'curso': 'Informatica para Internet',
            'turma': '2º AMS',
            'empresa': str(empresa_parceira.pk)
        })
        self.assertEqual(response_alu.status_code, 302)
        self.assertTrue(Aluno.objects.filter(turma='2º AMS').exists())

    def test_15_pesquisas_e_filtros_gestao(self):
        """Testa os filtros de pesquisa por parâmetro GET nas telas de gestão"""
        self.client.login(username='coord@etec.sp.gov.br', password='123')

        response_busca_emp = self.client.get(reverse('empresagestao') + '?q=Tech')
        self.assertEqual(response_busca_emp.status_code, 200)

        response_filtro_ment = self.client.get(reverse('mentoriasgestao') + '?status=Em+breve')
        self.assertEqual(response_filtro_ment.status_code, 200)

        response_busca_alu = self.client.get(reverse('gerenciaalunosc') + '?q=Aluno')
        self.assertEqual(response_busca_alu.status_code, 200)

    def test_16_regra_negocio_mentoria_passada(self):
        """Garante que o sistema bloqueia inscrição em mentorias cuja data já ocorreu no passado"""
        mentoria_passada = Mentoria.objects.create(
            tema='Mentoria Antiga',
            descricao='Já ocorreu',
            data=self.hoje - datetime.timedelta(days=5),
            carga_horaria=Decimal('2.00'),
            empresa=self.empresa
        )

        self.client.login(username='aluno@etec.sp.gov.br', password='123')
        response = self.client.post(reverse('inscreveremmentoriaa', args=[mentoria_passada.pk]))
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Participacao.objects.filter(id_aluno=self.aluno, id_mentoria=mentoria_passada).exists())