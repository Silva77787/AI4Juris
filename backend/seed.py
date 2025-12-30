from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from api.models import Document, Group, GroupMembership


def _ensure_document(user, filename, group=None):
    existing = Document.objects.filter(user=user, filename=filename, group=group).first()
    if existing:
        return existing

    document = Document(
        user=user,
        group=group,
        filename=filename,
        state="DONE",
    )
    document.file.save(filename, ContentFile(b"dummy pdf content"), save=True)
    return document


def run():
    User = get_user_model()

    # Create 20 users (a..t) with password 1234.
    users = []
    for i in range(20):
        letter = chr(ord("a") + i)
        email = f"{letter}@gmail.com"
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "first_name": letter, "role": "user"},
        )
        user.email = email
        user.first_name = letter
        user.set_password("1234")
        user.save()
        users.append(user)

    # Create 5 groups with different owners.
    owners = users[:5]
    groups = []
    for idx, owner in enumerate(owners, start=1):
        group, _ = Group.objects.get_or_create(name=f"Grupo {idx}", defaults={"owner": owner})
        if group.owner_id != owner.id:
            group.owner = owner
            group.save()
        groups.append(group)
        GroupMembership.objects.get_or_create(
            user=owner,
            group=group,
            defaults={"role": "owner"},
        )

    # Assign each user to 2-3 groups.
    for i, user in enumerate(users):
        group_ids = {i % 5, (i + 1) % 5}
        if i % 2 == 0:
            group_ids.add((i + 2) % 5)
        for gid in group_ids:
            group = groups[gid]
            role = "owner" if group.owner_id == user.id else "member"
            GroupMembership.objects.get_or_create(
                user=user,
                group=group,
                defaults={"role": role},
            )

    # Personal uploads: 3-5 per user.
    for i, user in enumerate(users):
        count = 3 + (i % 3)
        for n in range(1, count + 1):
            filename = f"{user.first_name}_personal_{n}.pdf"
            _ensure_document(user, filename, group=None)

    # Group uploads: at least 1 per user in a group.
    for i, user in enumerate(users):
        group = groups[i % 5]
        filename = f"{user.first_name}_group_{group.id}.pdf"
        _ensure_document(user, filename, group=group)

    print("Database seeded successfully!")