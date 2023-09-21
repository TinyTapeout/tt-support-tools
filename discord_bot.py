#!/usr/bin/env python3

import os
import sys

import discord
import yaml

TOKEN = os.environ["DISCORD_TOKEN"]
TARG = os.environ["TARGET_SERVER"]
ROLE_ID = os.environ["ROLE_ID"]

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
exit_code = 0


@client.event
async def on_ready():
    global exit_code
    try:
        print(f"{client.user} has connected to Discord!")
        server = None
        for g in client.guilds:
            if g.name == TARG:
                server = g
                break
        if server is None:
            print(f"Error: Bot is not in a server named {TARG}")
            exit_code = 1
            await client.close()

        role = server.get_role(int(ROLE_ID))
        if not role:
            print("Error: requested role does not exist on server!")
            exit_code = 1
            await client.close()

        participants = []
        for project in os.listdir("./projects"):
            info_file = os.path.join("projects", project, "info.yaml")
            if not os.path.exists(info_file):
                print(f"info.yaml does not exist for project {project}. Skipping.")
            else:
                try:
                    stream = open(info_file, "r")
                    data = yaml.load(stream, Loader=yaml.FullLoader)
                    stream.close()
                    if "discord" in data["documentation"]:
                        dname = data["documentation"]["discord"]
                        if len(dname):
                            if "#" in dname:
                                dname = dname.split("#")[0]
                            #                            print(f'adding {dname}')
                            participants.append(dname)
                    else:
                        print(
                            f"Project {project} has no discord username listed. Skipping."
                        )
                except Exception as ex:
                    print(f"Error parsing info.yaml for project {project}. Skipping.")
                    print(f"Error was: {ex}")

        members = []
        for p in participants:
            for m in server.members:
                if m.name == p:
                    members.append(m)
                    break
                if m.global_name == p:
                    members.append(m)
                    break
            else:
                print(f"{p} not found in members")

        new_role_members = []
        for m in members:
            if len([d for d in m.roles if d.id == role.id]) == 0:
                print(f"Giving the role to {m.name}")
                new_role_members.append(m.name)
                await m.add_roles(
                    role, reason="Automatic role assignment by GitHub actions pipeline."
                )
            else:
                print(f"{m.name} already has role")

        print("All done!")
        print("gave new role to:")
        print("@" + " @".join(new_role_members))
        await client.close()
    except Exception as ex:
        print("Exception was thrown!")
        print(ex)
        exit_code = 1
        await client.close()


client.run(TOKEN)
sys.exit(exit_code)
