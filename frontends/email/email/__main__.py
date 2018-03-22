import flask

import secret


app = flask.Flask(__name__)


@app.route("/sns/cecibot-request-bot", methods=["POST"])
def email():
    key = flask.request.args.get("key")
    if key != secret.key:
        # I'm a teapot
        flask.abort(418)

    print(flask.request.data)
    print()
    print()


if __name__ == "__main__":
    app.run(port=3169)
