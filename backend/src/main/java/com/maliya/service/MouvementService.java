package com.maliya.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.maliya.config.Horloge;
import com.maliya.domaine.Mouvement;
import com.maliya.domaine.MouvementRepository;
import com.maliya.ia.IaClient;
import com.maliya.requetes.Requetes;
import com.maliya.web.ApiErreurs.Introuvable;

@Service
public class MouvementService {

    /** En dessous de ce score, on laisse le mouvement « à classer » plutôt que de deviner. */
    private static final double SEUIL_CONFIANCE = 0.35;

    private final MouvementRepository repo;
    private final NamedParameterJdbcTemplate jdbc;
    private final IaClient ia;
    private final Horloge horloge;

    public MouvementService(MouvementRepository repo, NamedParameterJdbcTemplate jdbc, IaClient ia, Horloge horloge) {
        this.repo = repo;
        this.jdbc = jdbc;
        this.ia = ia;
        this.horloge = horloge;
    }

    public record NouveauMouvement(Long structureId, LocalDate date, String libelle, BigDecimal montant,
                                   Long categorieId, Long projetId, Long clientId, String source) {
    }

    @Transactional
    public Map<String, Object> creer(NouveauMouvement n) {
        if (n.structureId() == null) {
            throw new IllegalArgumentException("Choisis la structure concernée (agence, société, projet ou perso).");
        }
        if (n.libelle() == null || n.libelle().isBlank()) {
            throw new IllegalArgumentException("Le libellé est vide.");
        }
        if (n.montant() == null || n.montant().signum() == 0) {
            throw new IllegalArgumentException("Le montant doit être différent de zéro.");
        }
        Mouvement m = new Mouvement();
        m.setStructureId(n.structureId());
        m.setCompteId(comptePrincipal(n.structureId()));
        m.setDateOp(n.date() != null ? n.date() : horloge.aujourdhui());
        m.setLibelle(n.libelle().trim());
        m.setMontant(n.montant().setScale(2, RoundingMode.HALF_UP));
        m.setProjetId(n.projetId());
        m.setClientId(n.clientId());
        m.setSource(n.source() != null ? n.source() : "MANUEL");
        if (n.categorieId() != null) {
            m.setCategorieId(n.categorieId());
        } else {
            ia.categoriser(m.getLibelle(), m.getMontant()).ifPresent(s -> appliquerSuggestion(m, s));
        }
        Mouvement enregistre = repo.save(m);
        return lire(enregistre.getId());
    }

    private void appliquerSuggestion(Mouvement m, Map<String, Object> s) {
        double confiance = ((Number) s.getOrDefault("confiance", 0)).doubleValue();
        Object categorieId = s.get("categorie_id");
        if (confiance >= SEUIL_CONFIANCE && categorieId != null) {
            m.setCategorieId(((Number) categorieId).longValue());
            m.setCategorieParIa(true);
            m.setConfianceIa(BigDecimal.valueOf(confiance).setScale(3, RoundingMode.HALF_UP));
        }
    }

    /** Une correction humaine remplace toujours la proposition de l'IA. */
    @Transactional
    public Map<String, Object> modifier(Long id, Long categorieId, Long projetId, boolean retirerProjet) {
        Mouvement m = repo.findById(id).orElseThrow(() -> new Introuvable("Mouvement " + id + " introuvable."));
        if (categorieId != null) {
            m.setCategorieId(categorieId);
            m.setCategorieParIa(false);
            m.setConfianceIa(null);
        }
        if (projetId != null) {
            m.setProjetId(projetId);
        } else if (retirerProjet) {
            m.setProjetId(null);
        }
        repo.save(m);
        return lire(id);
    }

    /** Accepte en bloc des propositions de l'IA (liste de {transactionId, categorieId, confiance}). */
    @Transactional
    public int validerPropositions(List<Map<String, Object>> propositions) {
        int n = 0;
        for (Map<String, Object> p : propositions) {
            Long id = ((Number) p.get("transactionId")).longValue();
            Long categorieId = ((Number) p.get("categorieId")).longValue();
            Optional<Mouvement> m = repo.findById(id);
            if (m.isPresent() && m.get().getCategorieId() == null) {
                m.get().setCategorieId(categorieId);
                m.get().setCategorieParIa(true);
                Object c = p.get("confiance");
                if (c instanceof Number nombre) {
                    m.get().setConfianceIa(BigDecimal.valueOf(nombre.doubleValue()).setScale(3, RoundingMode.HALF_UP));
                }
                repo.save(m.get());
                n++;
            }
        }
        return n;
    }

    public Map<String, Object> lire(Long id) {
        try {
            return jdbc.queryForMap(Requetes.MOUVEMENT_PAR_ID, new MapSqlParameterSource("id", id));
        } catch (EmptyResultDataAccessException e) {
            throw new Introuvable("Mouvement " + id + " introuvable.");
        }
    }

    private Long comptePrincipal(Long structureId) {
        try {
            return jdbc.queryForObject(Requetes.COMPTE_PRINCIPAL, new MapSqlParameterSource("sid", structureId), Long.class);
        } catch (EmptyResultDataAccessException e) {
            throw new IllegalArgumentException("Cette structure n'a pas encore de compte bancaire.");
        }
    }
}
