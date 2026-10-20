from datetime import timedelta
from decimal import Decimal
from io import BytesIO
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile
from .forms_platform import MAX_AVATAR_DIMENSION, MAX_AVATAR_SIZE, ChallengeForm
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

    def test_company_challenge_management_paginates_large_histories(self):
        deadline = timezone.now() + timedelta(days=7)
        Challenge.objects.bulk_create([
            Challenge(
                company=self.company,
                title=f"Desafio {number}",
                description="Descrição do desafio.",
                deadline=deadline,
            )
            for number in range(25)
        ])
        self.login_as(self.company_user)

        first_page = self.client.get(reverse("company_challenge_management"))
        second_page = self.client.get(reverse("company_challenge_management"), {"page": "2"})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["page_obj"].paginator.count, 26)
        self.assertEqual(len(first_page.context["challenges"]), 25)
        self.assertContains(first_page, 'aria-label="Paginação de resultados"')
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["challenges"]), 1)
        self.assertContains(second_page, "Página 2 de 2")

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
    @staticmethod
    def make_image(format="PNG", size=(32, 32)):
        image_data = BytesIO()
        Image.new("RGB", size, color="royalblue").save(image_data, format=format)
        return image_data.getvalue()

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

    def test_invalid_profile_submission_keeps_saved_photo_preview(self):
        self.login_as(self.dev_user)
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.developer.avatar.save(
                "saved.png",
                SimpleUploadedFile("saved.png", self.make_image(), content_type="image/png"),
                save=True,
            )
            saved_photo_url = self.developer.avatar.url
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "portfolio_url": "not-a-url",
                "avatar": SimpleUploadedFile(
                    "new.png", self.make_image(), content_type="image/png",
                ),
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, saved_photo_url)
            self.developer.refresh_from_db()
            self.assertEqual(self.developer.avatar.url, saved_photo_url)

    def test_developer_can_upload_profile_photo_and_company_sees_it(self):
        self.login_as(self.dev_user)
        image = SimpleUploadedFile("dev.png", self.make_image(), content_type="image/png")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "bio": "Perfil profissional",
                "skills": "",
                "technologies": "",
                "portfolio_url": "",
                "github_url": "",
                "linkedin_url": "",
                "website_url": "",
                "avatar": image,
            }, follow=True)
            self.assertEqual(response.status_code, 200)
            self.developer.refresh_from_db()
            self.assertTrue(self.developer.avatar.name.startswith("profile_photos/"))
            self.assertContains(response, self.developer.avatar.url)

            Participation.objects.create(challenge=self.challenge, developer=self.developer)
            self.login_as(self.company_user)
            response = self.client.get(reverse("company_challenge_manage", args=[self.challenge.pk]))
            self.assertContains(response, self.developer.avatar.url)

    def test_company_photo_appears_on_public_challenges_and_in_conversations(self):
        self.login_as(self.company_user)
        company_image = SimpleUploadedFile("company.png", self.make_image(), content_type="image/png")
        developer_image = SimpleUploadedFile("developer.png", self.make_image(), content_type="image/png")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Arena Tech",
                "avatar": company_image,
            })
            self.assertEqual(response.status_code, 302)
            self.company.refresh_from_db()
            company_photo_url = self.company.avatar.url
            self.developer.avatar.save("developer.png", developer_image, save=True)

            self.login_as(self.dev_user)
            for url in (
                reverse("challenge_list"),
                reverse("challenge_detail", args=[self.challenge.pk]),
            ):
                with self.subTest(url=url):
                    self.assertContains(self.client.get(url), company_photo_url)

            conversation = Conversation.objects.create(
                company=self.company, developer=self.developer, challenge=self.challenge,
            )
            self.assertContains(self.client.get(reverse("conversation_list")), company_photo_url)
            self.assertContains(
                self.client.get(reverse("conversation_detail", args=[conversation.pk])),
                company_photo_url,
            )

            self.login_as(self.company_user)
            self.assertContains(
                self.client.get(reverse("conversation_detail", args=[conversation.pk])),
                self.developer.avatar.url,
            )

    def test_profile_rejects_invalid_or_oversized_photos(self):
        self.login_as(self.dev_user)
        invalid_image = SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")
        with self.subTest(reason="invalid image"):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "avatar": invalid_image,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn("avatar", response.context["form"].errors)

        oversized_format = SimpleUploadedFile(
            "large.bmp", self.make_image(format="BMP", size=(32, 32)),
            content_type="image/bmp",
        )
        with self.subTest(reason="unsupported format"):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "avatar": oversized_format,
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "JPG, PNG ou WebP")

        large_image = BytesIO()
        Image.frombytes(
            "RGB", (1350, 1350), os.urandom(1350 * 1350 * 3)
        ).save(large_image, format="PNG")
        self.assertGreater(len(large_image.getvalue()), MAX_AVATAR_SIZE)
        oversized_file = SimpleUploadedFile(
            "large.png", large_image.getvalue(), content_type="image/png",
        )
        with self.subTest(reason="file size"):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "avatar": oversized_file,
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "no máximo 5 MB")

        oversized_dimensions = SimpleUploadedFile(
            "dimensions.png", self.make_image(size=(MAX_AVATAR_DIMENSION + 1, 1)),
            content_type="image/png",
        )
        with self.subTest(reason="image dimensions"):
            response = self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "avatar": oversized_dimensions,
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "4096 × 4096")

    def test_replacing_and_removing_photo_deletes_previous_upload(self):
        self.login_as(self.dev_user)
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            first_image = SimpleUploadedFile("first.png", self.make_image(), content_type="image/png")
            self.client.post(reverse("account_profile"), {
                "public_name": "Dev Público",
                "avatar": first_image,
            })
            self.developer.refresh_from_db()
            first_name = self.developer.avatar.name
            self.assertTrue(self.developer.avatar.storage.exists(first_name))

            second_image = SimpleUploadedFile("second.png", self.make_image(), content_type="image/png")
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response = self.client.post(reverse("account_profile"), {
                    "public_name": "Dev Público",
                    "avatar": second_image,
                })
            self.assertEqual(response.status_code, 302)
            self.developer.refresh_from_db()
            second_name = self.developer.avatar.name
            self.assertNotEqual(first_name, second_name)
            self.assertEqual(len(callbacks), 1)
            self.assertFalse(self.developer.avatar.storage.exists(first_name))

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse("account_profile"), {
                    "public_name": "Dev Público",
                    "remove_avatar": "on",
                })
            self.assertEqual(response.status_code, 302)
            self.developer.refresh_from_db()
            self.assertFalse(self.developer.avatar)
            self.assertFalse(self.developer.avatar.storage.exists(second_name))

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
    def signup_data(self, identifier_name, identifier_value):
        data = {
            "nome": "Conta de Teste",
            identifier_name: identifier_value,
            "email": f"{identifier_name}@example.test",
            "senha": "Complex-Test-Password-984!",
            "senha2": "Complex-Test-Password-984!",  # dev e empresa confirmam a senha
        }
        return data

    def test_company_signup_has_name_cnpj_email_password_and_password_confirmation(self):
        response = self.client.get(reverse("signup_company"))
        form = response.context["form"]
        self.assertEqual(list(form.fields), ["nome", "cnpj", "email", "senha", "senha2"])
        self.assertEqual(form.fields["nome"].label, "Nome da empresa")
        self.assertContains(response, 'name="senha2"')
        for name in ("cep", "logradouro", "numero", "bairro", "cidade", "uf", "cpf"):
            self.assertNotContains(response, f'name="{name}"')

    def test_company_signup_rejects_mismatched_password_confirmation(self):
        data = self.signup_data("cnpj", "04.252.011/0001-10")
        data["senha2"] = "Outra-Senha-Diferente-123!"
        response = self.client.post(reverse("signup_company"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "As senhas não coincidem.")
        self.assertFalse(Profile.objects.filter(user__email="cnpj@example.test").exists())

    def test_company_signup_saves_account_without_address(self):
        self.client.post(reverse("signup_company"), self.signup_data("cnpj", "04.252.011/0001-10"))
        profile = Profile.objects.get(user__email="cnpj@example.test")
        self.assertEqual(profile.user.first_name, "Conta de Teste")
        self.assertEqual((profile.cep, profile.logradouro, profile.uf), ("", "", ""))

    def test_developer_signup_does_not_ask_for_address(self):
        response = self.client.get(reverse("signup_dev"))
        self.assertNotContains(response, 'name="cep"')
        self.assertContains(response, 'name="senha2"')

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


class DeveloperSelectionTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.participation = Participation.objects.create(
            challenge=self.challenge, developer=self.developer,
        )

    def test_company_can_select_developer_after_review_and_open_one_conversation(self):
        Submission.objects.create(
            participation=self.participation,
            repository_url="https://github.com/example/solution",
            score=Decimal("87.50"),
            reviewed_at=timezone.now(),
        )
        self.login_as(self.company_user)
        url = reverse("company_select_developer", args=[self.participation.pk])

        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 302)

        self.participation.refresh_from_db()
        self.assertEqual(self.participation.status, Participation.STATUS_SELECTED)
        self.assertEqual(
            Conversation.objects.filter(
                company=self.company, developer=self.developer, challenge=self.challenge,
            ).count(),
            1,
        )

    def test_company_cannot_select_developer_before_review(self):
        Submission.objects.create(
            participation=self.participation,
            repository_url="https://github.com/example/solution",
        )
        self.login_as(self.company_user)

        response = self.client.post(
            reverse("company_select_developer", args=[self.participation.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.participation.refresh_from_db()
        self.assertEqual(self.participation.status, Participation.STATUS_REGISTERED)
        self.assertFalse(Conversation.objects.filter(challenge=self.challenge).exists())


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
        self.assertContains(response, "<title>DevCodeArena — Desafios de programação e oportunidades | Prog.</title>")
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'href="/static/favicon.svg"')
        self.assertContains(response, 'aria-label="DevCodeArena, plataforma da Prog."')
        self.assertContains(response, 'class="brand__mascot-face"')
        self.assertContains(response, 'id="cyber-shell"')
        self.assertContains(response, '<h1 class="hero__title" id="home-title"><span class="hero__title-highlight">DevCode</span>Arena</h1>')
        self.assertContains(response, '<p class="hero__headline">Hackathons que conectam talentos a oportunidades.</p>')
        self.assertContains(response, "Sou DEV")
        self.assertContains(response, "Sou empresa")
        self.assertContains(response, reverse("signup_dev"))
        self.assertContains(response, reverse("signup_company"))
        self.assertContains(response, "hero-visual")
        self.assertContains(response, "arena-podium")
        self.assertContains(response, "TALENTO EM DESTAQUE")
        self.assertContains(response, "Desafios reais")
        self.assertContains(response, "A empresa avalia")
        self.assertContains(response, "Entregas avaliadas")
        self.assertContains(response, "Seu trabalho fala mais alto.")
        self.assertContains(response, 'id="como-funciona"')
        self.assertContains(response, "data-tilt")
        # mão 3D abaixo da imagem da arena e coliseu na seção "uma arena, dois caminhos"
        self.assertContains(response, 'id="hero-scene"')
        self.assertContains(response, "models/hand.glb")
        self.assertContains(response, 'id="arena-scene"')
        self.assertContains(response, "three.module.js")
        self.assertContains(response, "home_motion.js")
        self.assertContains(response, "home_motion.js?v=5")
        self.assertNotContains(response, "gsap.min.js")

    def test_login_page_offers_both_account_types(self):
        response = self.client.get(reverse("login"), {"next": "/desafios/"})
        self.assertContains(response, "auth--choose")
        self.assertContains(response, reverse("login_dev") + "?next=/desafios/")
        self.assertContains(response, reverse("login_company") + "?next=/desafios/")
        self.assertContains(response, reverse("signup"))

    def test_homepage_does_not_repeat_login_and_signup_buttons_for_visitors(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        # o convite final ("próximo passo") só existe para quem já está logado
        self.assertNotIn('class="next-step"', html)
        # os cards de apresentação não carregam botões de cadastro/login
        main = html[html.index('<main'):html.index("</main>")]
        self.assertNotIn("Criar conta DEV", main)
        self.assertNotIn("Criar conta de empresa", main)
        self.assertNotIn("Escolher meu perfil", main)
        # o hero mantém os dois caminhos de cadastro e a pessoa ainda alcança o login pelo menu/rodapé
        self.assertEqual(main.count(reverse("signup_dev")), 1)
        self.assertEqual(main.count(reverse("signup_company")), 1)
        self.assertIn(reverse("login_dev"), html)
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

    def test_unconfigured_social_links_do_not_point_to_placeholder_urls(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "github.com/Prog.")
        self.assertNotContains(response, "linkedin.com/company/prog.")
        self.assertNotContains(response, "instagram.com/prog.")
