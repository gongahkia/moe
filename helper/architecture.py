from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.language import Python
from diagrams.onprem.container import Docker
from diagrams.custom import Custom

graph_attr = {
    "splines": "ortho",
    "nodesep": "2",
    "ranksep": "2",
    "pad": "1.0",
    "fontsize": "16",
}

with Diagram("Moe Architecture", show=True, direction="LR", graph_attr=graph_attr):
    user = User("User")
    discord_gateway = Custom("Discord Gateway", "./discord.png")
    steam_api = Custom("Steam API", "./steam.png")

    with Cluster("Docker Container"):
        docker = Docker("Docker Engine")
        with Cluster("Bot Services"):
            python_bot = Python("Discord Bot\n(Python)")
            redis_cache = Custom("Redis Cache\n(State & Rate Limiting)", "./redis.png")
            python_bot - Edge(color="brown", style="dashed") - redis_cache
        docker - python_bot
        docker - redis_cache

    # Use xlabel for all edges to keep labels off arrows
    user >> Edge(xlabel="1. /compare") >> discord_gateway
    discord_gateway >> Edge(xlabel="2. Process") >> python_bot
    python_bot >> Edge(xlabel="3. Check cache") >> redis_cache
    redis_cache >> Edge(xlabel="4a. Hit") >> python_bot
    python_bot >> Edge(xlabel="4b. Miss") >> steam_api
    steam_api >> Edge(xlabel="5. API resp.") >> python_bot
    python_bot >> Edge(xlabel="6. Update") >> redis_cache
    python_bot >> Edge(xlabel="7. Embed") >> discord_gateway
    discord_gateway >> Edge(xlabel="8. Result") >> user
