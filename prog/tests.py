from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile
from .forms_platform import ChallengeForm
from .forms_accounts import valid_cnpj

User = get_user_model()


class PlatformTestCase(TestCase):
    def setUp(self):
        self.company_user = User.objects.create_user(
            username="empresa@example.test", email="empresa@example.test", password="Teste-Seguro-123!"
        )
        self.company = Profile.objects.create(user=self.company_user, tipo=Profile.COMPANY, cpf="11111111111")
        self.dev_user = User.objects.create_user(
            username="dev@example.test", email="dev@example.test", password="Teste-Seguro-123!",
            first_name="Dev Público",
        )
        self.developer = Profile.objects.create(user=self.dev_user, tipo=Profile.DEVELOPER, cpf="22222222222")
        self.other_user = User.objects.create_user(
            username="outro@example.test", email="outro@example.test", password="Teste-Seguro-123!",
            first_name="Outro Dev",
        )
        self.other_developer = Profile.objects.create(
            user=self.other_user, tipo=Profile.DEVELOPER, cpf="33333333333"
        )
        now = timezone.now()
        self.challenge = Challenge.objects.create(
            company=self.company, title="API Challenge", description="Crie uma API REST.",
            deadline=now + timedelta(days=3), start_at=now - timedelta(hours=1),
            period=Challenge.PERIOD_WEEKLY, difficulty=Challenge.DIFFICULTY_INTERMEDIATE,
            status=Challenge.STATUS_PUBLISHED, is_active=True,
        )

    def login_as(self, user):
        self.client.force_login(user)


class ChallengeFlowTests(PlatformTestCase):
    def test_anonymous_visitor_is_sent_to_login_from_challenge_pages(self):
        for name, args in (("challenge_periods", ()), ("challenge_list", ()), ("challenge_detail", (self.challenge.pk,))):
            with self.subTest(page=name):
                url = reverse(name, args=args)
                self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_list_renders_published_challenge_for_logged_user(self):
        self.login_as(self.dev_user)
        response = self.client.get(reverse("challenge_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API Challenge")

    def test_company_dashboard_aggregates_metrics_correctly(self):
        first_participation = Participation.objects.create(
            challenge=self.challenge,
            developer=self.developer,
            status=Participation.STATUS_SELECTED,
        )
        second_participation = Participation.objects.create(
            challenge=self.challenge,
            developer=self.other_developer,
        )
        for participation in (first_participation, second_participation):
            Submission.objects.create(
                participation=participation,
                repository_url="https://github.com/example/project",
            )
        Challenge.objects.create(
            company=self.company,
            title="Desafio encerrado",
            description="Desafio concluído.",
            deadline=timezone.now() - timedelta(days=1),
            status=Challenge.STATUS_CLOSED,
            is_active=False,
        )
        Challenge.objects.create(
            company=self.company,
            title="Rascunho",
            description="Desafio não publicado.",
            deadline=timezone.now() + timedelta(days=1),
        )
        self.login_as(self.company_user)

        response = self.client.get(reverse("company_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_challenges"], 3)
        self.assertEqual(response.context["active_challenges"], 1)
        self.assertEqual(response.context["closed_challenges"], 1)
        self.assertEqual(response.context["participation_count"], 2)
        self.assertEqual(response.context["submission_count"], 2)
        self.assertEqual(response.context["selected_count"], 1)

    def test_developer_can_join_once(self):
        self.login_as(self.dev_user)
        url = reverse("challenge_join", args=[self.challenge.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(Participation.objects.filter(challenge=self.challenge, developer=self.developer).count(), 1)

    def test_company_cannot_join_as_developer(self):
        self.login_as(self.company_user)
        response = self.client.post(reverse("challenge_join", args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Participation.objects.filter(challenge=self.challenge).exists())

    def test_company_cannot_edit_another_companys_challenge(self):
        other_company_user = User.objects.create_user(username="outra-empresa", password="Teste-Seguro-123!")
        other_company = Profile.objects.create(
            user=other_company_user, tipo=Profile.COMPANY, cpf="44444444444"
        )
        challenge = Challenge.objects.create(
            company=other_company, title="Privado", description="Não editar.",
            deadline=timezone.now() + timedelta(days=2),
        )
        self.login_as(self.company_user)
        response = self.client.get(reverse("company_challenge_edit", args=[challenge.pk]))
        self.assertEqual(response.status_code, 404)

    def test_protected_page_redirects_to_account_type_login_selector(self):
        response = self.client.get(reverse("company_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('company_dashboard')}",
        )


class ProfileTests(PlatformTestCase):
    def test_profile_editor_is_personalized_for_developers_and_companies(self):
        self.company.cnpj = "12345678000195"
        self.company.save(update_fields=["cnpj"])
        for user, heading, field_label, identifier in (
            (self.dev_user, "Mostre o que você sabe fazer.", "Sobre você", self.developer.cpf),
            (self.company_user, "Dê identidade à sua empresa.", "Sobre a empresa", self.company.cnpj),
        ):
            with self.subTest(account=user.username):
                self.login_as(user)
                response = self.client.get(reverse("account_profile"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(response, field_label)
                self.assertContains(response, "PRÉVIA DO PERFIL")
                self.assertNotContains(response, identifier)

    def test_company_can_customize_its_public_profile(self):
        self.login_as(self.company_user)
        response = self.client.post(reverse("account_profile"), {
            "public_name": "Arena Tech",
            "bio": "Criamos ferramentas para equipes de tecnologia.",
            "skills": "Fintech, educação",
            "technologies": "Python, Django",
            "portfolio_url": "https://example.test/produtos",
            "github_url": "",
            "linkedin_url": "",
            "website_url": "https://example.test",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu perfil foi atualizado.")
        self.company.refresh_from_db()
        self.company_user.refresh_from_db()
        self.assertEqual(self.company.bio, "Criamos ferramentas para equipes de tecnologia.")
        self.assertEqual(self.company.skills, "Fintech, educação")
        self.assertEqual(self.company_user.first_name, "Arena Tech")

    def test_developer_can_update_professional_profile_without_exposing_private_data(self):
        self.login_as(self.dev_user)
        response = self.client.post(reverse("account_profile"), {
            "public_name": "Dev Atualizado",
            "bio": "Desenvolvedor focado em APIs.",
            "skills": "APIs, testes automatizados",
            "technologies": "Python, Django",
            "portfolio_url": "https://example.test/portfolio",
            "github_url": "https://github.com/dev",
            "linkedin_url": "https://linkedin.com/in/dev",
            "website_url": "",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu perfil foi atualizado.")
        self.developer.refresh_from_db()
        self.dev_user.refresh_from_db()
        self.assertEqual(self.developer.bio, "Desenvolvedor focado em APIs.")
        self.assertEqual(self.developer.skills, "APIs, testes automatizados")
        self.assertEqual(self.developer.technologies, "Python, Django")
        self.assertEqual(self.dev_user.first_name, "Dev Atualizado")
        self.assertNotContains(response, self.developer.cpf)

    def test_invalid_profile_url_is_rejected(self):
        self.login_as(self.dev_user)
        response = self.client.post(reverse("account_profile"), {
            "public_name": "Dev Público",
            "portfolio_url": "not-a-url",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe uma URL válida")
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.portfolio_url, "")

    def test_challenge_company_can_see_candidate_profile_but_not_private_data(self):
        self.developer.skills = "APIs, testes"
        self.developer.technologies = "Python, Django"
        self.developer.github_url = "https://github.com/dev"
        self.developer.save()
        Participation.objects.create(challenge=self.challenge, developer=self.developer)
        self.login_as(self.company_user)
        response = self.client.get(reverse("company_challenge_manage", args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APIs, testes")
        self.assertContains(response, "Python, Django")
        self.assertContains(response, "https://github.com/dev")
        self.assertNotContains(response, self.developer.cpf)
        self.assertNotContains(response, self.dev_user.email)


class SignupIdentifierTests(TestCase):
    ADDRESS = {
        "cep": "01310-100", "logradouro": "Avenida Paulista", "numero": "1000",
        "complemento": "Sala 2", "bairro": "Bela Vista", "cidade": "São Paulo", "uf": "sp",
    }

    def signup_data(self, identifier_name, identifier_value):
        data = {
            "nome": "Conta de Teste",
            identifier_name: identifier_value,
            "email": f"{identifier_name}@example.test",
            "senha": "Complex-Test-Password-984!",
            "senha2": "Complex-Test-Password-984!",
        }
        if identifier_name == "cnpj":  # empresa também informa o endereço
            data.update(self.ADDRESS)
        return data

    def test_company_signup_saves_normalized_address(self):
        self.client.post(reverse("signup_company"), self.signup_data("cnpj", "04.252.011/0001-10"))
        profile = Profile.objects.get(user__email="cnpj@example.test")
        self.assertEqual((profile.cep, profile.uf, profile.cidade), ("01310100", "SP", "São Paulo"))
        self.assertEqual(profile.logradouro, "Avenida Paulista")

    def test_company_signup_requires_address(self):
        data = self.signup_data("cnpj", "04.252.011/0001-10")
        for field in ("cep", "logradouro", "numero", "bairro", "cidade", "uf"):
            data.pop(field)
        response = self.client.post(reverse("signup_company"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Por favor, informe o CEP da empresa.")
        self.assertFalse(Profile.objects.filter(user__email="cnpj@example.test").exists())

    def test_company_signup_rejects_invalid_cep_and_uf(self):
        data = self.signup_data("cnpj", "04.252.011/0001-10") | {"cep": "123", "uf": "XX"}
        response = self.client.post(reverse("signup_company"), data)
        self.assertContains(response, "Informe um CEP válido (8 números).")
        self.assertContains(response, "Informe uma UF válida (ex.: SP).")

    def test_developer_signup_does_not_ask_for_address(self):
        response = self.client.get(reverse("signup_dev"))
        self.assertNotContains(response, 'name="cep"')

    def test_company_signup_requires_and_saves_cnpj_instead_of_cpf(self):
        response = self.client.post(
            reverse("signup_company"),
            self.signup_data("cnpj", "04.252.011/0001-10"),
        )
        self.assertRedirects(response, reverse("home"))
        profile = Profile.objects.get(user__email="cnpj@example.test")
        self.assertEqual(profile.tipo, Profile.COMPANY)
        self.assertEqual(profile.cnpj, "04252011000110")
        self.assertIsNone(profile.cpf)

    def test_company_signup_rejects_invalid_or_duplicate_cnpj(self):
        self.assertFalse(valid_cnpj("00000000000000"))
        data = self.signup_data("cnpj", "04.252.011/0001-10")
        self.assertRedirects(self.client.post(reverse("signup_company"), data), reverse("home"))
        self.client.logout()
        duplicate = self.signup_data("cnpj", "04252011000110")
        response = self.client.post(reverse("signup_company"), duplicate)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este CNPJ já está cadastrado.")
        self.assertEqual(Profile.objects.filter(cnpj="04252011000110").count(), 1)

    def test_developer_signup_still_requires_and_saves_cpf(self):
        response = self.client.post(
            reverse("signup_dev"),
            self.signup_data("cpf", "529.982.247-25"),
        )
        self.assertRedirects(response, reverse("home"))
        profile = Profile.objects.get(user__email="cpf@example.test")
        self.assertEqual(profile.tipo, Profile.DEVELOPER)
        self.assertEqual(profile.cpf, "52998224725")
        self.assertIsNone(profile.cnpj)

    def test_signup_pages_render_identifier_for_selected_account_type(self):
        company_response = self.client.get(reverse("signup_company"))
        self.assertContains(company_response, 'name="cnpj"')
        self.assertNotContains(company_response, 'name="cpf"')
        developer_response = self.client.get(reverse("signup_dev"))
        self.assertContains(developer_response, 'name="cpf"')
        self.assertNotContains(developer_response, 'name="cnpj"')


class ConversationSecurityTests(PlatformTestCase):
    def test_only_conversation_participants_can_read_messages(self):
        participation = Participation.objects.create(challenge=self.challenge, developer=self.developer)
        participation.status = Participation.STATUS_SELECTED
        participation.save()
        conversation = Conversation.objects.create(
            company=self.company, developer=self.developer, challenge=self.challenge
        )
        Message.objects.create(conversation=conversation, sender=self.company, body="Olá")
        self.login_as(self.other_user)
        self.assertEqual(
            self.client.get(reverse("conversation_detail", args=[conversation.pk])).status_code, 404
        )

    def test_participants_can_send_persistent_messages(self):
        conversation = Conversation.objects.create(
            company=self.company, developer=self.developer, challenge=self.challenge
        )
        self.login_as(self.dev_user)
        response = self.client.post(
            reverse("conversation_detail", args=[conversation.pk]), {"body": "Olá, equipe!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Message.objects.filter(conversation=conversation, body="Olá, equipe!").exists())


class RankingTests(PlatformTestCase):
    def test_ranking_uses_only_reviewed_scores(self):
        participation = Participation.objects.create(challenge=self.challenge, developer=self.developer)
        Submission.objects.create(
            participation=participation, repository_url="https://github.com/example/solution",
            score=Decimal("87.50"), reviewed_at=timezone.now(),
        )
        self.login_as(self.dev_user)
        response = self.client.get(reverse("leaderboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dev Público")
        self.assertContains(response, "87,50")

    def test_unreviewed_submissions_do_not_appear_in_ranking(self):
        participation = Participation.objects.create(challenge=self.challenge, developer=self.developer)
        Submission.objects.create(participation=participation, repository_url="https://github.com/example/solution")
        self.login_as(self.dev_user)
        response = self.client.get(reverse("leaderboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Dev Público")



class ChallengeManagementTests(PlatformTestCase):
    def _challenge_payload(self, deadline):
        return {
            "title": "Novo desafio integrado",
            "description": "Construa uma API para um caso real.",
            "reward": "150.00",
            "start_at": "",
            "deadline": timezone.localtime(deadline).strftime("%Y-%m-%dT%H:%M"),
            "period": Challenge.PERIOD_MONTHLY,
            "difficulty": Challenge.DIFFICULTY_BEGINNER,
            "languages": "Python",
            "technologies": "Django",
            "requirements": "Entregar endpoints REST.",
            "evaluation_criteria": "Clareza, testes e documentação.",
        }

    def test_company_can_publish_challenge(self):
        self.login_as(self.company_user)
        payload = self._challenge_payload(timezone.now() + timedelta(days=5))
        payload["action"] = "publish"
        response = self.client.post(reverse("company_challenge_create"), payload)
        self.assertRedirects(response, reverse("company_challenge_management"))
        challenge = Challenge.objects.get(title="Novo desafio integrado")
        self.assertEqual(challenge.company, self.company)
        self.assertEqual(challenge.status, Challenge.STATUS_PUBLISHED)
        self.assertTrue(challenge.is_active)
        self.assertEqual(challenge.period, Challenge.PERIOD_MONTHLY)

    def test_company_cannot_publish_challenge_with_past_deadline(self):
        self.login_as(self.company_user)
        payload = self._challenge_payload(timezone.now() - timedelta(days=1))
        payload["action"] = "publish"
        response = self.client.post(reverse("company_challenge_create"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data futura de encerramento")
        self.assertFalse(Challenge.objects.filter(title="Novo desafio integrado").exists())

    def test_language_filter_uses_get_parameters(self):
        self.challenge.languages = "Python"
        self.challenge.save()
        Challenge.objects.create(
            company=self.company,
            title="Desafio de JavaScript",
            description="Crie uma interface.",
            deadline=timezone.now() + timedelta(days=4),
            start_at=timezone.now() - timedelta(hours=1),
            languages="JavaScript",
            status=Challenge.STATUS_PUBLISHED,
            is_active=True,
        )
        self.login_as(self.dev_user)
        response = self.client.get(reverse("challenge_list"), {"language": "Python"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API Challenge")
        self.assertNotContains(response, "Desafio de JavaScript")


class ChallengeFormValidationTests(TestCase):
    def test_deadline_must_be_after_start(self):
        now = timezone.localtime(timezone.now())
        start_at = now + timedelta(days=3)
        deadline = now + timedelta(days=2)
        form = ChallengeForm(data={
            "title": "Datas inválidas",
            "description": "Teste de validação de datas.",
            "reward": "0.00",
            "start_at": start_at.strftime("%Y-%m-%dT%H:%M"),
            "deadline": deadline.strftime("%Y-%m-%dT%H:%M"),
            "period": Challenge.PERIOD_WEEKLY,
            "difficulty": Challenge.DIFFICULTY_BEGINNER,
            "languages": "Python",
            "technologies": "Django",
            "requirements": "",
            "evaluation_criteria": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("deadline", form.errors)

class NavigationTests(PlatformTestCase):
    def test_challenge_pages_have_accessible_lightweight_3d_visual(self):
        self.login_as(self.dev_user)
        for url_name in ("challenge_periods", "challenge_list"):
            with self.subTest(page=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'role="img"')
                self.assertContains(response, "challenge-visual__core")
                self.assertContains(response, "challenge-visual__code")
                self.assertNotContains(response, "three.module.js")
                self.assertNotContains(response, "models/hand.glb")

    def test_homepage_uses_lightweight_visual_and_has_paths_for_both_audiences(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criar perfil DEV")
        self.assertContains(response, "Criar perfil de empresa")
        self.assertContains(response, "hero-visual")
        self.assertContains(response, "arena-podium")
        self.assertContains(response, "TALENTO EM DESTAQUE")
        self.assertContains(response, "data-tilt")
        # mão 3D abaixo da imagem da arena e coliseu na seção "uma arena, dois caminhos"
        self.assertContains(response, 'id="hero-scene"')
        self.assertContains(response, "models/hand.glb")
        self.assertContains(response, 'id="arena-scene"')
        self.assertContains(response, "three.module.js")
        self.assertContains(response, "home_motion.js")

    def test_login_page_offers_both_account_types(self):
        response = self.client.get(reverse("login"), {"next": "/desafios/"})
        self.assertContains(response, "auth--choose")
        self.assertContains(response, reverse("login_dev") + "?next=/desafios/")
        self.assertContains(response, reverse("login_company") + "?next=/desafios/")
        self.assertContains(response, reverse("signup"))

    def test_homepage_next_step_never_sends_visitor_to_logged_area(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        block = html[html.index('class="next-step"'):html.index("</section>", html.index('class="next-step"'))]
        self.assertIn(reverse("signup"), block)
        self.assertIn(reverse("login"), block)
        self.assertNotIn(reverse("challenge_periods"), block)
        self.assertNotIn(reverse("leaderboard"), html[html.index("site-footer"):])

    def test_homepage_next_step_for_logged_developer_goes_to_challenges(self):
        self.login_as(self.dev_user)
        html = self.client.get(reverse("home")).content.decode()
        block = html[html.index('class="next-step"'):html.index("</section>", html.index('class="next-step"'))]
        self.assertIn(reverse("challenge_periods"), block)
        self.assertNotIn(reverse("signup"), block)

    def test_authenticated_developer_sees_header_navigation(self):
        self.login_as(self.dev_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Navegação principal"')
        self.assertContains(response, reverse("challenge_periods"))
        self.assertContains(response, reverse("conversation_list"))
        self.assertContains(response, reverse("leaderboard"))

    def test_authenticated_user_without_profile_still_sees_general_navigation(self):
        legacy_user = User.objects.create_user(
            username="legacy@example.test", email="legacy@example.test", password="Teste-Seguro-123!"
        )
        self.login_as(legacy_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Navegação principal"')
        self.assertContains(response, reverse("challenge_periods"))
        self.assertContains(response, reverse("logout"))
        self.assertNotContains(response, reverse("conversation_list"))
