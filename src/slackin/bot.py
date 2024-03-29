#!/usr/bin/env python3
from flask import Flask, request, make_response, Response
from slackeventsapi import SlackEventAdapter
from slack import WebClient, RTMClient
import json
from . import VERSION
from os import system, popen
import subprocess, time

import re
dm = {}

class Bot(object):
    app = None
    client = None
    def __init__(self, name=None, slack_token=None, signing_secret=None, host='127.0.0.1', port=8000, debug=False):
        assert name is not None, "Please give the bot a name"
        assert signing_secret is not None, "Muszę mieć signing secret by żyć"
        assert slack_token is not None, "Muszę mieć slack token secret by żyć"
        self.slack_token = slack_token
        self.host = host
        self.port = port
        self.debug = debug
        self.name = name
        self.app = Flask(name)
        self.rtm = RTMClient(token=self.slack_token)
        self.client = WebClient(token=slack_token)
        self.eventListener = SlackEventAdapter(signing_secret=signing_secret, endpoint="/slack/events", server=self.app)

        @self.app.route('/', methods=['GET'])
        def index():
            return make_response(f"Slack Integration Bot v{VERSION}", 200)

        


        #Nałuchiwanie na odpowiedz z wiadomości z przyciskiem
        @self.app.route("/slack/message_actions", methods=["POST"])
        def message_actions():

            data = json.loads(request.form["payload"])
            rt = data['type']
            if rt == "dialog_submission":
                mess = self.client.chat_postMessage(
                    channel=data["channel"]["id"],
                    text=f"Dziękujemy za formularz: {data['submission']}"
                )
            elif rt == "interactive_message" and data['callback_id'] == "start":
                dm[data['user']['name']] = data["channel"]["id"]
            elif rt == "interactive_message":
                om = data['original_message']
                at = om['attachments']
                ci = at[0]['callback_id']
                cmd = []
                if ci.startswith("fromSelect:"):
                    cmd = ci.replace("fromSelect:",'')
                    cmd = eval(cmd)
                print(at)
                n = 1
                elements = []
                for e in cmd:
                    if e == 'form':
                        pass
                    elif e == 'cbox':
                        elements.append(
                            {
                                "label": "Prawda/Fałsz",
                                "name": f"el_{e}_{n}",
                                "type": "select",
                                "value": "1",
                                "placeholder": "",
                                "options": [
                                    {
                                        "label": "Prawda",
                                        "value": "1"
                                    },
                                    {
                                        "label": "Fałsz",
                                        "value": "2"
                                    }

                                ]
                            }
                        )
                    elif e == 'select':
                        elements.append(
                            {
                                "label": "Imię zwierzątka",
                                "name": f"el_{e}_{n}",
                                "type": "select",
                                "value": "2",
                                "placeholder": "Wybierz imię",
                                "options": [
                                    {
                                        "label": "Ala",
                                        "value": "1"
                                    },
                                    {
                                        "label": "Ola",
                                        "value": "2"
                                    }

                                ]
                            }
                        )
                    elif e == 'text':
                        elements.append(
                            {
                            "label": "Input text",
                            "name": f"el_{e}_{n}",
                            "type": "text",
                            "placeholder": "Wpisz cokolwiek"
                            }
                        )
                    elif e == 'area':
                        elements.append(
                            {
                            "label": "Input textarea",
                            "name": f"el_{e}_{n}",
                            "type": "textarea",
                            "placeholder": "Wpisz cokolwiek"
                            }
                        )
                    n += 1

                dialog = {
                        "title": "Formularz",
                        "submit_label": "Wyślij",
                        "callback_id": "formCallback",
                        "elements": elements
                }
                form1 = self.client.dialog_open(
                    trigger_id = data["trigger_id"],
                    dialog = dialog
                )
            else:
                print(f"nieznany typ messaga {rt}")
            return make_response("", 200)


        @self.eventListener.on("message")
        def message(event_data):
            try:
                args = re.split(r'\W+',event_data["event"]["text"])
            except KeyError:
                return
            channel = event_data["event"]["channel"]
            try:
                bot_name = args[0]
                command = args[1]
                try:
                    args = args[2:]
                except IndexError:
                    args = []
            except IndexError:
                return
            if not (bot_name in [self.name, 'all']):
                return
            try:
                cmd = getattr(self, f"cmd_{command}")
            except AttributeError:
                pass
            else:
                resp = cmd(event_data=event_data, args=args)
                if type(resp) == str and resp:
                    mess = self.client.chat_postMessage(
                        channel=event_data["event"]["channel"],
                        text=resp
                    )
                else:
                    mess = self.client.chat_postMessage(
                        channel=event_data["event"]["channel"],
                        text=f"Błędna odpowiedź z komendy {command}"
                    )
            return


    def run(self):
        self.app.run(host=self.host, port=self.port, debug=self.debug)

        


def main():
    import argparse, sys
    parser = argparse.ArgumentParser(prog='slackin', description='Slack integration bot')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument('-i', '--ip', type=str, help='Hostname or ip for bot app to listen on. Default: 127.0.0.1', default='127.0.0.1')
    parser.add_argument('-n', '--name', type=str, help='Slack bot name. Default: "bot".', default='bot')
    parser.add_argument('-p', '--port', type=int, help='Port number for bot app to listen on. Default: 8000.', default=8000)
    parser.add_argument('-s', '--secret', type=str, help='Slack signing_secret value', required=True)
    parser.add_argument('-t', '--token', type=str, help='Slack token value', required=True)
    args = parser.parse_args()

    class MyBot(Bot):
        def cmd_hello(self, event_data=None, args=[]):
            return "Hello dude!"
        def cmd_xd(self, event_data=None, args=[]):
            return "Hello xd!"
        def cmd_pat(self, event_data=None, args=[]):
            return "Nie pij tyle!"
        def cmd_update(self, event_data=None, args=[]):
            print('ls ' + ' '.join(args))
            odp = None
            myShellCmd = subprocess.run(['ls ', ' '.join(args)], shell=True, stdout=subprocess.PIPE , stderr=subprocess.STDOUT)
            if myShellCmd.returncode == 0:
                opd = myShellCmd.stdout
            elif myShellCmd.returncode != 1:
                opd = f'Błąd: {myShellCmd.stdout}'
            else:
                opd = "Nieznany błąd komendy"
            return str(opd)

    bot = MyBot(name=args.name, port=args.port, host=args.ip, slack_token=args.token, signing_secret=args.secret, debug=True)
    bot.run()