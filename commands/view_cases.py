import discord
from discord import app_commands
import database
import settings

MAX_DESCRIPTION_LENGTH = 4000  # Slightly below Discord limit

async def setup(bot):
    @bot.tree.command(
        name="view_cases",
        description="View all current cases (ID and Name only)."
    )
    async def view_cases(interaction: discord.Interaction):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return

        cases = database.get_all_cases()
        if not cases:
            await interaction.response.send_message("No cases found.", ephemeral=True)
            return

        # Format: `ID` `Name`
        case_lines = [f"`{case[0]}` `{case[1]}`" for case in cases]

        embeds = []
        current_desc = ""
        for line in case_lines:
            # If adding this line exceeds the limit, start a new embed
            if len(current_desc) + len(line) + 1 > MAX_DESCRIPTION_LENGTH:
                embed = discord.Embed(
                    title="Current Cases",
                    description=current_desc,
                    color=discord.Color.blue()
                )
                embeds.append(embed)
                current_desc = ""
            current_desc += line + "\n"

        # Add the last embed
        if current_desc:
            embed = discord.Embed(
                title="Current Cases",
                description=current_desc,
                color=discord.Color.blue()
            )
            embeds.append(embed)

        # Send all embeds, respecting ephemeral
        for i, embed in enumerate(embeds):
            if i == 0:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
