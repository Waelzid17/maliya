package com.maliya.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.Map;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.maliya.config.Horloge;
import com.maliya.domaine.Facture;
import com.maliya.domaine.FactureRepository;
import com.maliya.domaine.Mouvement;
import com.maliya.domaine.MouvementRepository;
import com.maliya.requetes.Requetes;
import com.maliya.web.ApiErreurs.Introuvable;

@Service
public class FactureService {

    private final FactureRepository factures;
    private final MouvementRepository mouvements;
    private final NamedParameterJdbcTemplate jdbc;
    private final Horloge horloge;

    public FactureService(FactureRepository factures, MouvementRepository mouvements,
                          NamedParameterJdbcTemplate jdbc, Horloge horloge) {
        this.factures = factures;
        this.mouvements = mouvements;
        this.jdbc = jdbc;
        this.horloge = horloge;
    }

    public record NouvelleFacture(Long structureId, Long clientId, Long projetId, String objet,
                                  BigDecimal montantHt, BigDecimal tvaTaux, LocalDate dateEmission, Integer delaiJours) {
    }

    @Transactional
    public Facture creer(NouvelleFacture n) {
        if (n.structureId() == null || n.clientId() == null) {
            throw new IllegalArgumentException("Une facture a besoin d'une structure et d'un client.");
        }
        if (n.montantHt() == null || n.montantHt().signum() <= 0) {
            throw new IllegalArgumentException("Le montant HT doit être positif.");
        }
        LocalDate emission = n.dateEmission() != null ? n.dateEmission() : horloge.aujourdhui();
        Facture f = new Facture();
        f.setNumero(prochainNumero(n.structureId(), emission.getYear()));
        f.setStructureId(n.structureId());
        f.setClientId(n.clientId());
        f.setProjetId(n.projetId());
        f.setObjet(n.objet() == null || n.objet().isBlank() ? "Prestation" : n.objet().trim());
        f.setDateEmission(emission);
        f.setDateEcheance(emission.plusDays(n.delaiJours() != null ? n.delaiJours() : 30));
        f.setMontantHt(n.montantHt().setScale(2, RoundingMode.HALF_UP));
        if (n.tvaTaux() != null) {
            f.setTvaTaux(n.tvaTaux());
        }
        return factures.save(f);
    }

    /** Marque la facture payée et inscrit l'encaissement dans le grand livre, en une seule transaction. */
    @Transactional
    public Facture encaisser(Long id, LocalDate date) {
        Facture f = factures.findById(id).orElseThrow(() -> new Introuvable("Facture " + id + " introuvable."));
        if (f.getDatePaiement() != null) {
            throw new IllegalStateException("La facture " + f.getNumero() + " est déjà payée.");
        }
        LocalDate jour = date != null ? date : horloge.aujourdhui();
        f.setDatePaiement(jour);
        f.setStatut("PAYEE");

        String client = jdbc.queryForObject("SELECT nom FROM client WHERE id = :id",
                new MapSqlParameterSource("id", f.getClientId()), String.class);
        Mouvement m = new Mouvement();
        m.setStructureId(f.getStructureId());
        m.setCompteId(jdbc.queryForObject(Requetes.COMPTE_PRINCIPAL,
                new MapSqlParameterSource("sid", f.getStructureId()), Long.class));
        m.setDateOp(jour);
        m.setLibelle("VIR RECU " + (client == null ? "" : client.toUpperCase()) + " " + f.getNumero());
        m.setMontant(f.montantTtc());
        m.setCategorieId(jdbc.queryForObject(Requetes.CATEGORIE_PAR_CODE,
                new MapSqlParameterSource("code", "REV_CLIENT"), Long.class));
        m.setClientId(f.getClientId());
        m.setProjetId(f.getProjetId());
        m.setSource("MANUEL");
        mouvements.save(m);
        return factures.save(f);
    }

    private String prochainNumero(Long structureId, int annee) {
        String prefixe;
        try {
            String dernier = jdbc.queryForObject(Requetes.DERNIER_NUMERO,
                    new MapSqlParameterSource("sid", structureId), String.class);
            prefixe = dernier != null && dernier.contains("-") ? dernier.substring(0, dernier.indexOf('-')) : "F" + structureId;
        } catch (EmptyResultDataAccessException e) {
            prefixe = "F" + structureId;
        }
        for (int i = 1; i < 10000; i++) {
            String numero = String.format("%s-%d-%03d", prefixe, annee, i);
            Long existe = jdbc.queryForObject(Requetes.NUMERO_EXISTE, new MapSqlParameterSource("numero", numero), Long.class);
            if (existe == null || existe == 0) {
                return numero;
            }
        }
        throw new IllegalStateException("Impossible de trouver un numéro de facture libre.");
    }

    public Map<String, Object> resume(Facture f) {
        return Map.of("id", f.getId(), "numero", f.getNumero(), "statut", f.getStatut(),
                "montantTtc", f.montantTtc());
    }
}
