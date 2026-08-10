from admin import load_admins, is_admin

data = load_admins()
print("Admins enregistrés :", data["admins"])

test_user = "alxd"
if is_admin(test_user):
    print(f"{test_user} est bien admin ✅")
else:
    print(f"{test_user} n'est PAS admin ❌")
