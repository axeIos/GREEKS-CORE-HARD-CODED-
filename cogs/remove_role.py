import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import typing

LOGO = "<:GreeksLogo:1505682080330420244>"

class RoleManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_role_everyone", description="Add a role to all server members")
    @app_commands.describe(role="Role to add to everyone")
    @app_commands.default_permissions(administrator=True)
    async def add_role_everyone(self, interaction: discord.Interaction, role: discord.Role):
        if role == interaction.guild.default_role:
            await interaction.response.send_message("You cannot add @everyone as a role.", ephemeral=True)
            return

        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role. I cannot add it.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        members_without_role = [m for m in interaction.guild.members if role not in m.roles and not m.bot]

        if not members_without_role:
            await interaction.followup.send(f"Everyone already has {role.mention}.", ephemeral=True)
            return

        await interaction.followup.send(f"Adding {role.mention} to {len(members_without_role)} members... This may take a moment.", ephemeral=True)

        added = 0
        failed = 0

        for member in members_without_role:
            try:
                await member.add_roles(role, reason=f"Add role everyone by {interaction.user}")
                added += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                print(f"Failed to add role to {member}: {e}")

        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {LOGO} Add Role Completed"))
        container.add_item(discord.ui.TextDisplay(f"**Role:** {role.mention}\n**Added:** {added}\n**Failed:** {failed}"))
        view.add_item(container)

        await interaction.followup.send(view=view, ephemeral=True)

    @app_commands.command(name="remove_role_everyone", description="Remove a role from all server members")
    @app_commands.describe(role="Role to remove from everyone")
    @app_commands.default_permissions(administrator=True)
    async def remove_role_everyone(self, interaction: discord.Interaction, role: discord.Role):
        if role == interaction.guild.default_role:
            await interaction.response.send_message("You cannot remove @everyone.", ephemeral=True)
            return

        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role. I cannot remove it.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        members_with_role = [m for m in interaction.guild.members if role in m.roles]

        if not members_with_role:
            await interaction.followup.send(f"No one has {role.mention}.", ephemeral=True)
            return

        await interaction.followup.send(f"Removing {role.mention} from {len(members_with_role)} members... This may take a moment.", ephemeral=True)

        removed = 0
        failed = 0

        for member in members_with_role:
            try:
                await member.remove_roles(role, reason=f"Remove role everyone by {interaction.user}")
                removed += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                print(f"Failed to remove role from {member}: {e}")

        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## {LOGO} Remove Role Completed"))
        container.add_item(discord.ui.TextDisplay(f"**Role:** {role.mention}\n**Removed:** {removed}\n**Failed:** {failed}"))
        view.add_item(container)

        await interaction.followup.send(view=view, ephemeral=True)

    @app_commands.command(name="add_role_member", description="Add a role to a specific member")
    @app_commands.describe(member="Member to add the role to", role="Role to add")
    @app_commands.default_permissions(manage_roles=True)
    async def add_role_member(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role.", ephemeral=True)
            return

        if role in member.roles:
            await interaction.response.send_message(f"{member.mention} already has {role.mention}.", ephemeral=True)
            return

        try:
            await member.add_roles(role, reason=f"Added by {interaction.user}")
            view = discord.ui.LayoutView(timeout=None)
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {LOGO} Role Added"))
            container.add_item(discord.ui.TextDisplay(f"**Member:** {member.mention}\n**Role:** {role.mention}\n**Added by:** {interaction.user.mention}"))
            view.add_item(container)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to add role: {e}", ephemeral=True)

    @app_commands.command(name="remove_role_member", description="Remove a role from a specific member")
    @app_commands.describe(member="Member to remove the role from", role="Role to remove")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_role_member(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role.", ephemeral=True)
            return

        if role not in member.roles:
            await interaction.response.send_message(f"{member.mention} does not have {role.mention}.", ephemeral=True)
            return

        try:
            await member.remove_roles(role, reason=f"Removed by {interaction.user}")
            view = discord.ui.LayoutView(timeout=None)
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(f"## {LOGO} Role Removed"))
            container.add_item(discord.ui.TextDisplay(f"**Member:** {member.mention}\n**Role:** {role.mention}\n**Removed by:** {interaction.user.mention}"))
            view.add_item(container)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to remove role: {e}", ephemeral=True)

    @app_commands.command(name="add_role_members", description="Add a role to multiple members")
    @app_commands.describe(role="Role to add", member1="First member", member2="Second member", member3="Third member", member4="Fourth member", member5="Fifth member")
    @app_commands.default_permissions(manage_roles=True)
    async def add_role_members(self, interaction: discord.Interaction, role: discord.Role, member1: discord.Member, member2: typing.Optional[discord.Member] = None, member3: typing.Optional[discord.Member] = None, member4: typing.Optional[discord.Member] = None, member5: typing.Optional[discord.Member] = None):
        members = [m for m in [member1, member2, member3, member4, member5] if m]

        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        added = 0
        for member in members:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Added by {interaction.user}")
                    added += 1
                except:
                    pass

        await interaction.followup.send(f"Added {role.mention} to {added}/{len(members)} members.", ephemeral=True)

    @app_commands.command(name="remove_role_members", description="Remove a role from multiple members")
    @app_commands.describe(role="Role to remove", member1="First member", member2="Second member", member3="Third member", member4="Fourth member", member5="Fifth member")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_role_members(self, interaction: discord.Interaction, role: discord.Role, member1: discord.Member, member2: typing.Optional[discord.Member] = None, member3: typing.Optional[discord.Member] = None, member4: typing.Optional[discord.Member] = None, member5: typing.Optional[discord.Member] = None):
        members = [m for m in [member1, member2, member3, member4, member5] if m]

        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"Role {role.mention} is above my role.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        removed = 0
        for member in members:
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"Removed by {interaction.user}")
                    removed += 1
                except:
                    pass

        await interaction.followup.send(f"Removed {role.mention} from {removed}/{len(members)} members.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleManagementCog(bot))