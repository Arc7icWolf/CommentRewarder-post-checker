import time
import requests
import json
from datetime import datetime, timedelta
import logging

# logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("main.log", mode="a")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# Send request, get response
def get_response(data, session: requests.Session):
    urls = [
        "https://api.deathwing.me",
        "https://api.hive.blog",
        "https://hive-api.arcange.eu",
        "api.openhive.network",
    ]
    for url in urls: # If an API doesn't work, try the next one
        request = requests.Request("POST", url=url, data=data).prepare()
        response_json = session.send(request, allow_redirects=False)
        if response_json.status_code == 502:
            continue
        response = response_json.json()["result"]
        return response


# Get the number of comments upvoted by the post's author
def get_active_votes_num(author, permlink, session: requests.Session):
    data = f'{{"jsonrpc":"2.0", "method":"condenser_api.get_content_replies", "params":["{author}", "{permlink}"], "id":1}}'
    replies = get_response(data, session)
    active_votes_num = 0
    for reply in replies:
        active_votes = reply.get("active_votes", [])
        if active_votes:
            for active_vote in active_votes:
                if active_vote["voter"] == author:
                    active_votes_num += 1
    return active_votes_num


def get_posts(session: requests.Session):
    today = datetime.now()
    twentyfour_hours = today - timedelta(hours=24) # Change if you want check a different timeframe

    less_than_twentyfour_hours = True
    posts_list = []
    author = ""
    permlink = ""
    i = 1
    while less_than_twentyfour_hours: # Loop until there are posts less than 24 old
        data = f'{{"jsonrpc":"2.0", "method":"bridge.get_ranked_posts", "params":{{"sort":"created","tag":"","observer":"", "start_author":"{author}", "start_permlink":"{permlink}"}}, "id":1}}'
        posts = get_response(data, session)
        for post in posts:
            if post["beneficiaries"] is not None:
                for beneficiary in post["beneficiaries"]:
                    if (
                        beneficiary["account"] == "commentrewarder"
                        and beneficiary["weight"] >= 300 # Skip posts with beneficiary set at less than 3%
                    ):
                        beneficiary_weight = beneficiary["weight"] / 100
                        author = post["author"]
                        permlink = post["permlink"]
                        created = post["created"]
                        created_formatted = datetime.strptime(
                            created, "%Y-%m-%dT%H:%M:%S"
                        )
                        if created_formatted < twentyfour_hours:
                            less_than_twentyfour_hours = False
                            print("Posts published in the last 24 hours with @commentrewarder as beneficiary:")
                            break

                        payout = post["pending_payout_value"].split()[0]
                        children = post["children"]
                        active_votes_num = 0
                        # If there are replies, check how many got upvoted by the author
                        if children > 0:
                            active_votes_num = get_active_votes_num(
                                author, permlink, session
                            )
                        if active_votes_num > 0:
                            optional = ""
                            rewards_shared = (
                                float(payout) * beneficiary_weight / 200
                            ) / active_votes_num
                        else:
                            optional = " (potentially)"
                            rewards_shared = float(payout) * beneficiary_weight / 200

                        post_link = (
                            f"{i}) https://www.peakd.com/@{author}/{permlink} with {active_votes_num} replies upvoted"
                            f" out of {children} replies: {rewards_shared} HBD{optional} going on average to each upvoted comment\n"
                        )
                        i += 1
                        posts_list.append(post_link)

            # Pagination system
            author = post["author"]
            permlink = post["permlink"]
    return posts_list


def main():
    start = time.time()

    try:
        with requests.Session() as session:
            posts = get_posts(session)
            for post in posts:
                print(post)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"JSON decode error or missing key: {e}")

    elapsed_time = time.time() - start
    print(f"Work completed in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
