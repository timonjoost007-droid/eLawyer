import discord
from discord import app_commands
import database
import settings

MAX_DESCRIPTION_LENGTH = 4000  # Slightly less than 4096 to be safe

async def setup(bot):
    @bot.tree.command(name="view_contacts", description="View all contacts/parties.")
    async def view_contacts(interaction: discord.Interaction):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
        
        contacts = database.get_all_contacts()
        if not contacts:
            await interaction.response.send_message("No contacts found.", ephemeral=True)
            return

        # Format each line: `ID` `Name` (`Status`)
        lines = [f"`{c[0]}` `{c[1]} ({c[4]})`" for c in contacts]

        embeds = []
        current_desc = ""
        for line in lines:
            # If adding this line exceeds the limit, start a new embed
            if len(current_desc) + len(line) + 1 > MAX_DESCRIPTION_LENGTH:
                embed = discord.Embed(
                    title="Contacts / Parties",
                    description=current_desc,
                    color=discord.Color.purple()
                )
                embeds.append(embed)
                current_desc = ""
            current_desc += line + "\n"

        # Add the last embed if any
        if current_desc:
            embed = discord.Embed(
                title="Contacts / Parties",
                description=current_desc,
                color=discord.Color.purple()
            )
            embeds.append(embed)

        # Send all embeds
        for embed in embeds:
            await interaction.response.send_message(embed=embed, ephemeral=True)
