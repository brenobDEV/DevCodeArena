from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms_platform import ChallengeForm, MessageForm, ReviewSubmissionForm, SubmissionForm
from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile


def _profile(request, required_type=None):
    profile = getattr(request.user, "dca_profile", None)
    if not profile or (required_type and profile.tipo != required_type):
        return None
    return profile


def _available_challenges():
    now = timezone.now()
    return Challenge.objects.select_related("company__user").filter(
        status=Challenge.STATUS_PUBLISHED, is_active=True, deadline__gte=now
    ).filter(Q(start_at__isnull=True) | Q(start_at__lte=now))


def challenge_periods(request):
    challenges = _available_challenges()
    weekly = challenges.filter(period=Challenge.PERIOD_WEEKLY)
    monthly = challenges.filter(period=Challenge.PERIOD_MONTHLY)
    return render(request, "platform/challenge_periods.html", {
        "weekly_count": weekly.count(), "monthly_count": monthly.count(),
        "weekly_challenges": weekly.order_by("deadline")[:3],
        "monthly_challenges": monthly.order_by("deadline")[:3],
    })


def challenge_list(request):
    now = timezone.now()
    challenges = Challenge.objects.select_related("company__user").filter(
        status__in=[Challenge.STATUS_PUBLISHED, Challenge.STATUS_CLOSED]
    )
    period = request.GET.get("period", "")
    language = request.GET.get("language", "").strip()[:80]
    technology = request.GET.get("technology", "").strip()[:80]
    difficulty = request.GET.get("difficulty", "")
    state = request.GET.get("state", "active")
    query = request.GET.get("q", "").strip()[:100]
    ordering = request.GET.get("ordering", "deadline")

    if state == "closed":
        challenges = challenges.filter(status=Challenge.STATUS_CLOSED)
    else:
        challenges = challenges.filter(status=Challenge.STATUS_PUBLISHED, is_active=True, deadline__gte=now)
        challenges = challenges.filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
        if state == "ending":
            challenges = challenges.filter(deadline__lte=now + timedelta(days=7))
    if period in dict(Challenge.PERIOD_CHOICES):
        challenges = challenges.filter(period=period)
    if difficulty in dict(Challenge.DIFFICULTY_CHOICES):
        challenges = challenges.filter(difficulty=difficulty)
    if language:
        challenges = challenges.filter(languages__icontains=language)
    if technology:
        challenges = challenges.filter(technologies__icontains=technology)
    if query:
        challenges = challenges.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
            | Q(company__user__first_name__icontains=query)
        )
    ordering_map = {"deadline": "deadline", "newest": "-created_at", "reward": "-reward"}
    page_obj = Paginator(challenges.order_by(ordering_map.get(ordering, "deadline"), "title"), 9).get_page(
        request.GET.get("page")
    )
    return render(request, "platform/challenge_list.html", {
        "page_obj": page_obj, "period_choices": Challenge.PERIOD_CHOICES,
        "difficulty_choices": Challenge.DIFFICULTY_CHOICES,
        "filters": {
            "q": query, "period": period, "language": language, "technology": technology,
            "difficulty": difficulty, "state": state, "ordering": ordering,
        },
    })


def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related("company__user"), pk=challenge_id)
    profile = _profile(request)
    if challenge.status == Challenge.STATUS_DRAFT:
        if not profile or profile.tipo != Profile.COMPANY or challenge.company_id != profile.id:
            raise Http404
    participation = None
    submission = None
    if profile and profile.tipo == Profile.DEVELOPER:
        participation = Participation.objects.filter(challenge=challenge, developer=profile).first()
        if participation:
            submission = Submission.objects.filter(participation=participation).first()
    return render(request, "platform/challenge_detail.html", {
        "challenge": challenge, "participation": participation, "submission": submission,
        "submission_form": SubmissionForm(instance=submission) if participation else None,
    })


@login_required
@require_POST
def challenge_join(request, challenge_id):
    profile = _profile(request, Profile.DEVELOPER)
    if not profile:
        return HttpResponseForbidden("Somente contas de desenvolvedor podem participar.")
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if not challenge.is_open:
        messages.error(request, "Este desafio não está aceitando novas participações.")
        return redirect("challenge_detail", challenge_id=challenge.pk)
    _, created = Participation.objects.get_or_create(challenge=challenge, developer=profile)
    messages.success(
        request,
        "Inscrição realizada. Envie o link da sua solução antes do prazo."
        if created else "Você já está inscrito neste desafio.",
    )
    return redirect("challenge_detail", challenge_id=challenge.pk)


@login_required
@require_POST
def challenge_submit(request, challenge_id):
    profile = _profile(request, Profile.DEVELOPER)
    if not profile:
        return HttpResponseForbidden("Somente contas de desenvolvedor podem enviar soluções.")
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    participation = get_object_or_404(Participation, challenge=challenge, developer=profile)
    if not challenge.is_open:
        messages.error(request, "O prazo deste desafio terminou ou ele não está publicado.")
        return redirect("challenge_detail", challenge_id=challenge.pk)
    submission = Submission.objects.filter(participation=participation).first()
    form = SubmissionForm(request.POST, instance=submission)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.participation = participation
        obj.submitted_at = timezone.now()
        obj.reviewed_at = None
        obj.score = None
        obj.feedback = ""
        obj.save()
        messages.success(request, "Sua submissão foi salva e ficará disponível para avaliação da empresa.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("challenge_detail", challenge_id=challenge.pk)


@login_required
def developer_submissions(request):
    profile = _profile(request, Profile.DEVELOPER)
    if not profile:
        return HttpResponseForbidden("Esta página é exclusiva para desenvolvedores.")
    participations = Participation.objects.filter(developer=profile).select_related(
        "challenge", "challenge__company__user", "submission"
    )
    return render(request, "platform/my_submissions.html", {"participations": participations})


@login_required
def account_profile(request):
    profile = _profile(request)
    if not profile:
        return HttpResponseForbidden("Esta conta não possui um perfil DevCodeArena válido.")
    return render(request, "platform/profile.html", {"profile": profile})


@login_required
def company_dashboard(request):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    own = Challenge.objects.filter(company=profile)
    now = timezone.now()
    context = {
        "total_challenges": own.count(),
        "active_challenges": own.filter(
            status=Challenge.STATUS_PUBLISHED, is_active=True, deadline__gte=now
        ).filter(Q(start_at__isnull=True) | Q(start_at__lte=now)).count(),
        "closed_challenges": own.filter(status=Challenge.STATUS_CLOSED).count(),
        "participation_count": Participation.objects.filter(challenge__company=profile).count(),
        "submission_count": Submission.objects.filter(participation__challenge__company=profile).count(),
        "selected_count": Participation.objects.filter(
            challenge__company=profile, status=Participation.STATUS_SELECTED
        ).count(),
        "recent_challenges": own.annotate(
            participant_count=Count("participations", distinct=True),
            submission_count=Count("participations__submission", distinct=True),
        ).order_by("-updated_at")[:5],
    }
    return render(request, "platform/company_dashboard.html", context)


@login_required
def company_challenge_create(request):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    return _company_challenge_form(request, profile, None)


@login_required
def company_challenge_edit(request, challenge_id):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    challenge = get_object_or_404(Challenge, pk=challenge_id, company=profile)
    return _company_challenge_form(request, profile, challenge)


def _company_challenge_form(request, profile, challenge):
    form = ChallengeForm(request.POST or None, instance=challenge)
    if request.method == "POST" and form.is_valid():
        publishing = request.POST.get("action", "draft") == "publish"
        obj = form.save(commit=False)
        obj.company = profile
        if publishing and obj.deadline <= timezone.now():
            form.add_error("deadline", "Para publicar, informe uma data futura de encerramento.")
        else:
            if publishing:
                if obj.start_at is None:
                    obj.start_at = timezone.now()
                obj.status = Challenge.STATUS_PUBLISHED
                obj.is_active = True
            else:
                obj.status = Challenge.STATUS_DRAFT
                obj.is_active = False
            obj.save()
            messages.success(request, "Desafio publicado." if publishing else "Rascunho salvo com sucesso.")
            return redirect("company_challenge_management")
    return render(request, "platform/company_challenge_form.html", {
        "form": form, "challenge": challenge, "is_edit": challenge is not None,
    })


@login_required
def company_challenge_management(request):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    challenges = Challenge.objects.filter(company=profile).annotate(
        participant_count=Count("participations", distinct=True),
        submission_count=Count("participations__submission", distinct=True),
    ).order_by("-updated_at")
    return render(request, "platform/company_challenge_management.html", {"challenges": challenges})


@login_required
def company_challenge_manage(request, challenge_id):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    challenge = get_object_or_404(Challenge, pk=challenge_id, company=profile)
    participations = Participation.objects.filter(challenge=challenge).select_related(
        "developer__user", "submission"
    ).order_by("-joined_at")
    return render(request, "platform/company_challenge_manage.html", {
        "challenge": challenge, "participations": participations,
    })


@login_required
@require_POST
def company_challenge_toggle(request, challenge_id):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    challenge = get_object_or_404(Challenge, pk=challenge_id, company=profile)
    if challenge.status == Challenge.STATUS_PUBLISHED:
        challenge.status = Challenge.STATUS_CLOSED
        challenge.is_active = False
        messages.success(request, "Desafio retirado do ar.")
    elif challenge.deadline <= timezone.now():
        messages.error(request, "Não é possível publicar um desafio com prazo encerrado.")
    else:
        challenge.status = Challenge.STATUS_PUBLISHED
        challenge.is_active = True
        if challenge.start_at is None:
            challenge.start_at = timezone.now()
        messages.success(request, "Desafio publicado.")
    challenge.save()
    return redirect("company_challenge_management")


@login_required
@require_POST
def company_select_developer(request, participation_id):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    participation = get_object_or_404(
        Participation.objects.select_related("challenge", "developer"),
        pk=participation_id, challenge__company=profile,
    )
    submission = Submission.objects.filter(participation=participation).first()
    if not submission or not submission.is_reviewed:
        messages.error(request, "Avalie a submissão antes de iniciar um contato de seleção.")
        return redirect("company_challenge_manage", challenge_id=participation.challenge_id)
    participation.status = Participation.STATUS_SELECTED
    participation.save(update_fields=["status", "updated_at"])
    Conversation.objects.get_or_create(
        company=profile, developer=participation.developer, challenge=participation.challenge
    )
    messages.success(request, "Desenvolvedor selecionado. A conversa foi habilitada.")
    return redirect("company_challenge_manage", challenge_id=participation.challenge_id)


@login_required
def company_review_submission(request, submission_id):
    profile = _profile(request, Profile.COMPANY)
    if not profile:
        return HttpResponseForbidden("Esta área é exclusiva para contas de empresa.")
    submission = get_object_or_404(
        Submission.objects.select_related("participation__challenge", "participation__developer__user"),
        pk=submission_id, participation__challenge__company=profile,
    )
    form = ReviewSubmissionForm(request.POST or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.reviewed_at = timezone.now()
        obj.save()
        messages.success(request, "Avaliação salva. A pontuação passa a contar no ranking.")
        return redirect("company_challenge_manage", challenge_id=submission.participation.challenge_id)
    return render(request, "platform/company_review_submission.html", {"form": form, "submission": submission})


@login_required
def conversation_list(request):
    profile = _profile(request)
    if not profile:
        return HttpResponseForbidden("Esta conta não possui um perfil DevCodeArena válido.")
    latest_message = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")
    conversations = Conversation.objects.filter(Q(company=profile) | Q(developer=profile)).select_related(
        "company__user", "developer__user", "challenge"
    ).annotate(
        last_message_body=Subquery(latest_message.values("body")[:1]),
        unread_count=Count(
            "messages", filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=profile),
            distinct=True,
        ),
    ).order_by("-updated_at")
    return render(request, "platform/conversation_list.html", {"conversations": conversations})


@login_required
def conversation_detail(request, conversation_id):
    profile = _profile(request)
    if not profile:
        return HttpResponseForbidden("Esta conta não possui um perfil DevCodeArena válido.")
    conversation = get_object_or_404(
        Conversation.objects.select_related("company__user", "developer__user", "challenge"),
        Q(pk=conversation_id) & (Q(company=profile) | Q(developer=profile)),
    )
    Message.objects.filter(conversation=conversation, read_at__isnull=True).exclude(
        sender=profile
    ).update(read_at=timezone.now())
    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = profile
        message.save()
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        return redirect("conversation_detail", conversation_id=conversation.pk)
    conversation_messages = conversation.messages.select_related("sender__user").order_by("created_at")
    return render(request, "platform/conversation_detail.html", {
        "conversation": conversation, "conversation_messages": conversation_messages, "form": form,
    })


@login_required
def leaderboard(request):
    reviewed = Q(participations__submission__score__isnull=False) & Q(
        participations__submission__reviewed_at__isnull=False
    )
    profiles = Profile.objects.filter(Q(tipo=Profile.DEVELOPER) & reviewed).select_related("user").annotate(
        total_score=Sum("participations__submission__score", filter=reviewed),
        reviewed_count=Count("participations__submission", filter=reviewed, distinct=True),
        completed_count=Count("participations__challenge", filter=reviewed, distinct=True),
    ).order_by("-total_score", "-completed_count", "created_at")
    return render(request, "platform/leaderboard.html", {"profiles": profiles})
