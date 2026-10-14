from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile
from .forms_platform import ChallengeForm

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
    def test_public_list_renders_published_challenge(self):
        response = self.client.get(reverse("challenge_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API Challenge")

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
