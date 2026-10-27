import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_PATH = "config.json"
GREEKS_LOGO = "<:GreeksLogo:1505682080330420244>"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"channels": {}, "roles": {}, "panel": {}}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def has_rules_permission(member, cfg):
    if member.guild_permissions.administrator:
        return True
    allowed = cfg.get("roles", {}).get("rules_allowed_roles", [])
    if not allowed:
        return True
    m_ids = [r.id for r in member.roles]
    return any(rid in m_ids for rid in allowed)

DISCORD_RULES = {
    1: {"cat": "SERVER RULES", "text": "Respect everyone. Treat all members with respect at all times."},
    2: {"cat": "SERVER RULES", "text": "No malicious links. Any IP grabbers, viruses, scams, or harmful software are strictly forbidden."},
    3: {"cat": "SERVER RULES", "text": "Do not mention @Owners or @Managers unless it is absolutely necessary."},
    4: {"cat": "SERVER RULES", "text": "Do not mention Staff without a valid reason."},
    5: {"cat": "GENERAL CONDUCT", "text": "Respect everyone's privacy. Sharing another member's personal information without permission is strictly prohibited."},
    6: {"cat": "GENERAL CONDUCT", "text": "No emoji or message spam. Keep the chat clean and readable."},
    7: {"cat": "GENERAL CONDUCT", "text": "Stay calm and respectful in voice chats. Excessive shouting, toxicity, or disruptive behavior is not allowed."},
    8: {"cat": "GENERAL CONDUCT", "text": "No mocking, harassment, or unnecessary sarcasm towards other members."},
    9: {"cat": "GENERAL CONDUCT", "text": "Avoid sensitive topics such as politics, religion, or fan-based arguments that may create conflict."},
    10: {"cat": "GENERAL CONDUCT", "text": "Racism, discrimination, hate speech, or offensive comments of any kind will not be tolerated."},
    11: {"cat": "GENERAL CONDUCT", "text": "Follow Staff instructions. Failure to comply may result in warnings or punishments."},
}

TEAM_RULES = {
    1: {"cat": "TEAM SYSTEM", "text": "Keep conversations game/work related. No unnecessary drama or off-topic chatting during matches."},
    2: {"cat": "TEAM SYSTEM", "text": "Do not claim or use roles you haven't been assigned."},
    3: {"cat": "TEAM SYSTEM", "text": "No random moves, mutes, kicks, or abuse of permissions."},
    4: {"cat": "TEAM SYSTEM", "text": "Respect everyone in voice chats. Insults, especially towards family members or the deceased, are strictly forbidden."},
    5: {"cat": "TEAM RULES", "text": "Respect and follow the decisions of Managers, Team Leaders & Higher Staff."},
    6: {"cat": "TEAM RULES", "text": "Help your teammates whenever they need support."},
    7: {"cat": "TEAM RULES", "text": "Respect experienced members - they earned their position and will respect you in return."},
    8: {"cat": "TEAM RULES", "text": "Promotions are earned, not requested. Stay active, loyal, and prove yourself."},
    9: {"cat": "TEAM RULES", "text": "No arguments, unnecessary toxicity, or creating drama inside the team."},
    10: {"cat": "REQUIREMENTS", "text": "Be active."},
    11: {"cat": "REQUIREMENTS", "text": "Stay loyal to the team."},
    12: {"cat": "REQUIREMENTS", "text": "Maintain a good level of gameplay."},
    13: {"cat": "REQUIREMENTS", "text": "Play with confidence and always give your best."},
    14: {"cat": "REQUIREMENTS", "text": "Support your teammates at all times."},
    15: {"cat": "REQUIREMENTS", "text": "Represent the team with respect, both in-game and outside of it."},
    16: {"cat": "REQUIREMENTS", "text": "One Team - One Goal - One Family"},
}

def make_embed(rules_dict, num, title_prefix):
    data = rules_dict.get(num)
    if not data:
        return None
    embed = discord.Embed(
        title=f"{GREEKS_LOGO} {title_prefix} {num} - {data['cat']}",
        description=f"**{num}.** {data['text']}",
    )
    embed.set_footer(text="GREEKS NETWORK | All rights reserved")
    return embed

class DiscordRulesView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        main = discord.ui.Container()
        main.add_item(discord.ui.TextDisplay(f"# {GREEKS_LOGO} DISCORD RULES"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay("## SERVER RULES\n1. Respect everyone.\n2. No malicious links.\n3. Do not mention @Owners or @Managers unless necessary.\n4. Do not mention Staff without valid reason."))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay("## GENERAL CONDUCT\n5. Respect privacy.\n6. No spam.\n7. Stay calm in voice.\n8. No mocking.\n9. Avoid sensitive topics.\n10. No racism.\n11. Follow Staff."))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay("-# GREEKS NETWORK | All rights reserved"))
        self.add_item(main)

class TeamRulesView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        main = discord.ui.Container()
        main.add_item(discord.ui.TextDisplay(f"# {GREEKS_LOGO} TEAM RULES"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay("## TEAM SYSTEM\n1. Game/work related.\n2. Do not claim roles.\n3. No random moves.\n4. Respect in voice."))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay("## TEAM RULES\n5. Respect decisions.\n6. Help teammates.\n7. Respect experienced.\n8. Promotions earned.\n9. No drama."))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        main.add_item(discord.ui.TextDisplay("## REQUIREMENTS\n10. Be active.\n11. Stay loyal.\n12. Good gameplay.\n13. Play with confidence.\n14. Support teammates.\n15. Represent team.\n16. One Team One Goal One Family"))
        main.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        main.add_item(discord.ui.TextDisplay("-# GREEKS NETWORK | All rights reserved"))
        self.add_item(main)

class RulesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.bot.add_view(DiscordRulesView())
            self.bot.add_view(TeamRulesView())
        except:
            pass

    @app_commands.command(name="setup_rules_roles", description="Set 3 roles that can use rules commands")
    @app_commands.describe(role1="Role 1", role2="Role 2", role3="Role 3")
    @app_commands.default_permissions(administrator=True)
    async def setup_rules_roles(self, interaction: discord.Interaction, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        cfg = load_config()
        if "roles" not in cfg:
            cfg["roles"] = {}
        roles_list = [role1.id]
        if role2:
            roles_list.append(role2.id)
        if role3:
            roles_list.append(role3.id)
        cfg["roles"]["rules_allowed_roles"] = roles_list
        save_config(cfg)
        names = ", ".join([r.name for r in [role1, role2, role3] if r])
        await interaction.followup.send(f"Allowed roles: {names}", ephemeral=True)

    @app_commands.command(name="rule", description="Show Discord single rule (1-11)")
    @app_commands.describe(number="Rule number 1-11")
    async def rule_slash(self, interaction: discord.Interaction, number: int):
        cfg = load_config()
        if not has_rules_permission(interaction.user, cfg):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        embed = make_embed(DISCORD_RULES, number, "Discord Rule")
        if not embed:
            await interaction.response.send_message(f"Discord Rule {number} not found. Use 1-11.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trule", description="Show Team single rule (1-16)")
    @app_commands.describe(number="Team rule number 1-16")
    async def trule_slash(self, interaction: discord.Interaction, number: int):
        cfg = load_config()
        if not has_rules_permission(interaction.user, cfg):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        embed = make_embed(TEAM_RULES, number, "Team Rule")
        if not embed:
            await interaction.response.send_message(f"Team Rule {number} not found. Use 1-16.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="panel_discord_rules", description="Send Discord Rules panel")
    async def panel_discord_rules(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        cfg = load_config()
        if not has_rules_permission(interaction.user, cfg):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        await target.send(view=DiscordRulesView())
        await interaction.followup.send("Discord Rules sent", ephemeral=True)

    @app_commands.command(name="panel_team_rules", description="Send Team Rules panel")
    async def panel_team_rules(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        cfg = load_config()
        if not has_rules_permission(interaction.user, cfg):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        await target.send(view=TeamRulesView())
        await interaction.followup.send("Team Rules sent", ephemeral=True)

    @commands.command(name="rule")
    async def rule_prefix(self, ctx, number: int = None):
        cfg = load_config()
        if not has_rules_permission(ctx.author, cfg):
            return
        if number is None:
            await ctx.send("Use: !rule 1  (Discord 1-11)")
            return
        embed = make_embed(DISCORD_RULES, number, "Discord Rule")
        if not embed:
            await ctx.send(f"Discord Rule {number} not found. Use 1-11.")
            return
        await ctx.send(embed=embed)

    @commands.command(name="trule")
    async def trule_prefix(self, ctx, number: int = None):
        cfg = load_config()
        if not has_rules_permission(ctx.author, cfg):
            return
        if number is None:
            await ctx.send("Use: !trule 1  (Team 1-16)")
            return
        embed = make_embed(TEAM_RULES, number, "Team Rule")
        if not embed:
            await ctx.send(f"Team Rule {number} not found. Use 1-16.")
            return
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        content = message.content.lower().strip()
        cfg = load_config()
        if not has_rules_permission(message.author, cfg):
            return
        if content.startswith("!rule") and not content.startswith("!trule"):
            try:
                num_str = content.replace("!rule", "").strip()
                if not num_str.isdigit():
                    return
                num = int(num_str)
                embed = make_embed(DISCORD_RULES, num, "Discord Rule")
                if embed:
                    await message.channel.send(embed=embed)
            except:
                pass
        elif content.startswith("!trule"):
            try:
                num_str = content.replace("!trule", "").strip()
                if not num_str.isdigit():
                    return
                num = int(num_str)
                embed = make_embed(TEAM_RULES, num, "Team Rule")
                if embed:
                    await message.channel.send(embed=embed)
            except:
                pass

async def setup(bot):
    await bot.add_cog(RulesCog(bot))