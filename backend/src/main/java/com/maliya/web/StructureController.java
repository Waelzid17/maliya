package com.maliya.web;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Ajouter un intercalaire : une agence, une société, un projet ou le perso, avec son compte bancaire. */
@RestController
@RequestMapping("/api/structures")
public class StructureController {

    private static final Set<String> TYPES = Set.of("AGENCE", "SOCIETE", "PROJET", "PERSO");
    private static final List<String> COULEURS = List.of("#3B5BA9", "#2E8B6F", "#D99A1E", "#8A4F7D", "#B8323F", "#1E7A8C");

    private final NamedParameterJdbcTemplate jdbc;

    public StructureController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public record NouvelleStructure(String nom, String type, String couleur, String ice,
                                    String banque, BigDecimal soldeInitial) {
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Transactional
    public Map<String, Object> creer(@RequestBody NouvelleStructure n) {
        if (n.nom() == null || n.nom().isBlank()) {
            throw new IllegalArgumentException("Donne un nom à cette structure.");
        }
        String type = n.type() == null ? "" : n.type().toUpperCase();
        if (!TYPES.contains(type)) {
            throw new IllegalArgumentException("Le type doit être AGENCE, SOCIETE, PROJET ou PERSO.");
        }
        Long existantes = jdbc.queryForObject("SELECT COUNT(*) FROM structure", new MapSqlParameterSource(), Long.class);
        String couleur = n.couleur() != null && n.couleur().matches("#[0-9A-Fa-f]{6}") ? n.couleur()
                : COULEURS.get((int) ((existantes == null ? 0 : existantes) % COULEURS.size()));
        Long id = jdbc.queryForObject("""
                INSERT INTO structure (nom, type, couleur, ice) VALUES (:nom, :type, :couleur, :ice) RETURNING id
                """, new MapSqlParameterSource()
                .addValue("nom", n.nom().trim())
                .addValue("type", type)
                .addValue("couleur", couleur)
                .addValue("ice", n.ice()), Long.class);
        jdbc.queryForObject("""
                INSERT INTO compte_bancaire (structure_id, nom, banque, solde_initial)
                VALUES (:sid, 'Compte principal', :banque, :solde) RETURNING id
                """, new MapSqlParameterSource()
                .addValue("sid", id)
                .addValue("banque", n.banque())
                .addValue("solde", n.soldeInitial() == null ? BigDecimal.ZERO : n.soldeInitial()), Long.class);
        return Map.of("id", id, "nom", n.nom().trim(), "type", type, "couleur", couleur);
    }
}
