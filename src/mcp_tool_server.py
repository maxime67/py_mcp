import asyncio
from mcp.server.fastmcp import FastMCP

# --- 1. La base de données locale du serveur ---
# C'est la seule source de vérité pour les données des films.
FILM_DATABASE = {
    1: {
        "title": "Matrix",
        "synopsis": """
        Programmeur anonyme dans un service administratif le jour, Thomas Anderson devient Neo la nuit venue. 
        Sous ce pseudonyme, il est l'un des pirates les plus recherchés du cyber-espace. A cheval entre deux mondes, 
        Neo est assailli par d'étranges songes et des messages cryptés provenant d'un certain Morpheus. 
        Celui-ci l'exhorte à aller au-delà des apparences et à trouver la réponse à la question qui hante 
        constamment ses pensées : qu'est-ce que la Matrice ?
        """
    },
    2: {
        "title": "Inception",
        "synopsis": """
        Dom Cobb est un voleur expérimenté – le meilleur qui soit dans l'art périlleux de l'extraction : 
        sa spécialité consiste à s'approprier les secrets les plus précieux d'un individu, enfouis au plus 
        profond de son subconscient, pendant qu'il rêve et que son esprit est particulièrement vulnérable.
        """
    }
}

# --- 2. Création du serveur MCP ---
async def main():
    mcp = FastMCP("movies-mcp-server", json_response=True, port=12345)

    # --- 3. Définition de l'unique outil ---
    # Cet outil ne fait aucune analyse, il retourne juste le synopsis d'un film, donné son ID.
    @mcp.tool()
    def mcp_get_film_synopsis(film_id: int) -> dict:
        """
        Retourne les informations d'un film (titre et synopsis) à partir de son ID.

        Args:
            film_id: L'identifiant du film (1 pour Matrix, 2 pour Inception)

        Returns:
            Un dictionnaire contenant le titre et le synopsis du film
        """
        if film_id in FILM_DATABASE:
            return FILM_DATABASE[film_id]
        else:
            return {"error": f"Film avec l'ID {film_id} non trouvé"}

    # --- 4. Démarrage du serveur ---
    print("Serveur de données MCP démarré sur le port 12345...")
    print("Ce terminal est maintenant dédié au serveur. Laissez-le tourner.")
    await mcp.run_streamable_http_async()

if __name__ == "__main__":
    asyncio.run(main())
