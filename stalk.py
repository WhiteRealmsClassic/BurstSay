import datetime
import requests


DISCORD_API = "https://discord.com/api/v10"
DISCORD_EPOCH = 1420070400000


def discord_headers(bot_token):
    return {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
        "User-Agent": "BurstSay/1.0"
    }


def snowflake_created_at(user_id):
    timestamp_ms = (int(user_id) >> 22) + DISCORD_EPOCH

    return datetime.datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=datetime.timezone.utc
    )


def account_age(created_at):
    now = datetime.datetime.now(datetime.timezone.utc)

    days = (now - created_at).days

    years = days // 365
    remaining_days = days % 365

    months = remaining_days // 30

    if years > 0:
        if months > 0:
            return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
        return f"{years} year{'s' if years != 1 else ''}"

    if months > 0:
        return f"{months} month{'s' if months != 1 else ''}"

    return f"{max(days, 0)} day{'s' if days != 1 else ''}"


def truncate(value, limit=1024):
    if value is None:
        return None

    value = str(value)

    if len(value) <= limit:
        return value

    return value[:limit - 3] + "..."


def premium_name(value):
    premium_types = {
        0: "None",
        1: "Nitro Classic",
        2: "Nitro",
        3: "Nitro Basic"
    }

    return premium_types.get(
        value,
        f"Type {value}"
    )


def flag_names(flags):
    if not flags:
        return "None"

    flags = int(flags)

    known_flags = {
        1 << 0: "Staff",
        1 << 1: "Partner",
        1 << 2: "HypeSquad Events",
        1 << 3: "Bug Hunter",
        1 << 6: "HypeSquad Bravery",
        1 << 7: "HypeSquad Brilliance",
        1 << 8: "HypeSquad Balance",
        1 << 9: "Early Supporter",
        1 << 10: "Team User",
        1 << 14: "Bug Hunter Gold",
        1 << 17: "Verified Bot",
        1 << 18: "Early Verified Bot Developer",
        1 << 19: "Moderator Programs Alumni",
        1 << 22: "Active Developer",
    }

    result = []

    for bit, name in known_flags.items():
        if flags & bit:
            result.append(name)

    return ", ".join(result) if result else "None"


def avatar_url(user):
    user_id = user.get("id")
    avatar = user.get("avatar")

    if not user_id or not avatar:
        return None

    extension = "gif" if avatar.startswith("a_") else "png"

    return (
        f"https://cdn.discordapp.com/avatars/"
        f"{user_id}/{avatar}.{extension}?size=1024"
    )


def banner_url(user):
    user_id = user.get("id")
    banner = user.get("banner")

    if not user_id or not banner:
        return None

    extension = "gif" if banner.startswith("a_") else "png"

    return (
        f"https://cdn.discordapp.com/banners/"
        f"{user_id}/{banner}.{extension}?size=1024"
    )


def get_user(bot_token, user_id):
    response = requests.get(
        f"{DISCORD_API}/users/{user_id}",
        headers=discord_headers(bot_token),
        timeout=15
    )

    if response.status_code == 404:
        return None, "That Discord user does not exist."

    if response.status_code == 401:
        return None, "BurstSay's bot token was rejected by Discord."

    if not response.ok:
        return None, (
            f"Discord returned HTTP {response.status_code} "
            "while fetching that user."
        )

    return response.json(), None


def get_member(bot_token, guild_id, user_id):
    if not guild_id:
        return None

    response = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
        headers=discord_headers(bot_token),
        timeout=15
    )

    if response.status_code == 404:
        return None

    if not response.ok:
        return None

    return response.json()


def get_roles(bot_token, guild_id):
    if not guild_id:
        return []

    response = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/roles",
        headers=discord_headers(bot_token),
        timeout=15
    )

    if not response.ok:
        return []

    return response.json()


def build_stalk_embed(
    bot_token,
    user_id,
    guild_id=None,
    guild_name=None
):
    user, error = get_user(
        bot_token,
        user_id
    )

    if error:
        return None, error

    actual_id = str(user.get("id", user_id))

    username = user.get(
        "username",
        "Unknown"
    )

    display_name = user.get(
        "global_name"
    ) or username

    created_at = snowflake_created_at(
        actual_id
    )

    created_timestamp = int(
        created_at.timestamp()
    )

    avatar = avatar_url(user)
    banner = banner_url(user)

    member = get_member(
        bot_token,
        guild_id,
        actual_id
    )

    roles = []

    if member and guild_id:
        role_ids = {
            str(role_id)
            for role_id in member.get(
                "roles",
                []
            )
        }

        guild_roles = get_roles(
            bot_token,
            guild_id
        )

        for role in guild_roles:
            if str(role.get("id")) in role_ids:
                roles.append(role)

        roles.sort(
            key=lambda role: role.get(
                "position",
                0
            ),
            reverse=True
        )

    embed = {
        "title": "🕵️ BurstSay • User Stalk",
        "description": (
            f"### {display_name}\n"
            f"`@{username}`\n\n"
            f"🔗 <@{actual_id}>"
        ),
        "color": 0x5865F2,
        "fields": [],
        "footer": {
            "text": "BurstSay • Public Discord information"
        },
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
    }

    if avatar:
        embed["thumbnail"] = {
            "url": avatar
        }

    if banner:
        embed["image"] = {
            "url": banner
        }

    # ------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------

    embed["fields"].append({
        "name": "👤 Identity",
        "value": (
            f"**Display:** {truncate(display_name, 256)}\n"
            f"**Username:** `{truncate(username, 256)}`\n"
            f"**ID:** `{actual_id}`"
        ),
        "inline": True
    })

    # ------------------------------------------------------------
    # ACCOUNT
    # ------------------------------------------------------------

    embed["fields"].append({
        "name": "📅 Account",
        "value": (
            f"**Created:** <t:{created_timestamp}:F>\n"
            f"**Age:** {account_age(created_at)}\n"
            f"**Type:** "
            f"{'Bot' if user.get('bot') else 'User'}"
        ),
        "inline": True
    })

    # ------------------------------------------------------------
    # DISCORD STATUS / FLAGS
    # ------------------------------------------------------------

    embed["fields"].append({
        "name": "✨ Discord",
        "value": (
            f"**Premium:** "
            f"{premium_name(user.get('premium_type', 0))}\n"
            f"**Flags:** "
            f"{truncate(flag_names(user.get('public_flags')), 900)}"
        ),
        "inline": False
    })

    # ------------------------------------------------------------
    # SERVER
    # ------------------------------------------------------------

    if member and guild_id:
        nickname = member.get("nick")

        joined_at = member.get(
            "joined_at"
        )

        server_value = (
            f"**Mutual server:** "
            f"{guild_name or 'This server'}\n"
            f"**Nickname:** "
            f"{truncate(nickname or 'None', 500)}"
        )

        if joined_at:
            try:
                joined_dt = datetime.datetime.fromisoformat(
                    joined_at.replace(
                        "Z",
                        "+00:00"
                    )
                )

                joined_timestamp = int(
                    joined_dt.timestamp()
                )

                server_value += (
                    f"\n**Joined:** "
                    f"<t:{joined_timestamp}:F>"
                )

            except Exception:
                pass

        embed["fields"].append({
            "name": "🏠 Server",
            "value": server_value,
            "inline": True
        })

        # --------------------------------------------------------
        # ROLES
        # --------------------------------------------------------

        if roles:
            role_text = []

            for role in roles[:20]:
                role_text.append(
                    f"<@&{role['id']}>"
                )

            if len(roles) > 20:
                role_text.append(
                    f"...and {len(roles) - 20} more"
                )

            embed["fields"].append({
                "name": "🎭 Roles",
                "value": "\n".join(role_text),
                "inline": True
            })

            highest_role = roles[0]

            embed["fields"].append({
                "name": "👑 Highest Role",
                "value": (
                    f"<@&{highest_role['id']}>"
                ),
                "inline": True
            })

        else:
            embed["fields"].append({
                "name": "🎭 Roles",
                "value": "No additional roles.",
                "inline": True
            })

    else:
        embed["fields"].append({
            "name": "🏠 Server",
            "value": (
                "No mutual server could be checked here.\n"
                "This command was used outside a server."
            ),
            "inline": True
        })

    # ------------------------------------------------------------
    # PROFILE DATA LIMITATION
    # ------------------------------------------------------------

    embed["fields"].append({
        "name": "🌐 Public Profile",
        "value": (
            "Discord does not expose every profile feature "
            "to bots through the standard API.\n\n"
            "🔒 Bio, wishlist, private friends, arbitrary "
            "connected accounts and global presence are not "
            "assumed unless Discord provides them to BurstSay."
        ),
        "inline": False
    })

    # ------------------------------------------------------------
    # PROFILE LINK
    # ------------------------------------------------------------

    embed["fields"].append({
        "name": "🔗 Profile",
        "value": (
            f"[Open Discord Profile]"
            f"(https://discord.com/users/{actual_id})"
        ),
        "inline": False
    })

    return embed, None
