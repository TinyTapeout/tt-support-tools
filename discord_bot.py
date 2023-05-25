#!/usr/bin/env python3

import os
import sys
import logging
import discord
import yaml
import re

TOKEN = os.environ['DISCORD_TOKEN']
TARG = os.environ['TARGET_SERVER']
ROLE_ID = os.environ['ROLE_ID']

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
exit_code = 0

@client.event
async def on_ready():
	try:
		print(f'{client.user} has connected to Discord!')
		server = None
		for g in client.guilds:
			if g.name == TARG:
				server = g
				break
		if server == None:
			print(f'Error: Bot is not in a server named {TARG}')
			exit_code = 1
			await client.close()
		
		role = server.get_role(int(ROLE_ID))
		if not role:
			print('Error: requested role does not exist on server!')
			exit_code = 1
			await client.close()
		
		participants = []
		for project in os.listdir('./projects'):
			info_file = os.path.join('projects', project, 'info.yaml')
			if not os.path.exists(info_file):
				print(f'info.yaml does not exist for project {project}. Skipping.')
			else:
				try:
					stream = open(info_file, 'r')
					data = yaml.load(stream, Loader=yaml.FullLoader)
					stream.close()
					dname = data['documentation']
					if 'discord' in dname:
						dname = dname['discord']
						parts = dname.split('#')
						if len(parts) != 2 or len(parts[0]) == 0 or not re.match('^[0-9]{4}$', parts[1]):
							print(f'Invalid format for discord username {dname} in project {project}. Skipping.')
						else:
							participants.append({'name': parts[0], 'discriminator': parts[1]})
					else:
						print(f'Project {project} has no discord username listed. Skipping.')
				except Exception as ex:
					print(f'Error parsing info.yaml for project {project}. Skipping.')
					print(f'Error was: {ex}')
		
		for m in server.members:
			a = [d for d in participants if d['name'] == m.name and d['discriminator'] == m.discriminator]
			if len(a) != 0:
				if len([d for d in m.roles if d.id == role.id]) == 0:
					print(f'Giving the role to {m.name}#{m.discriminator}')
					await m.add_roles(role, reason='Automatic role assignment by GitHub actions pipeline.')

		print('All done!')
		await client.close()
	except Exception as ex:
		print('Exception was thrown!')
		print(ex)
		exit_code = 1
		await client.close()

client.run(TOKEN)
sys.exit(exit_code)
