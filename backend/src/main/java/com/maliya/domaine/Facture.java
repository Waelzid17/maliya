package com.maliya.domaine;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "facture")
public class Facture {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String numero;

    @Column(name = "structure_id", nullable = false)
    private Long structureId;

    @Column(name = "client_id", nullable = false)
    private Long clientId;

    @Column(name = "projet_id")
    private Long projetId;

    @Column(nullable = false)
    private String objet;

    @Column(name = "date_emission", nullable = false)
    private LocalDate dateEmission;

    @Column(name = "date_echeance", nullable = false)
    private LocalDate dateEcheance;

    @Column(name = "date_paiement")
    private LocalDate datePaiement;

    @Column(name = "montant_ht", nullable = false, precision = 14, scale = 2)
    private BigDecimal montantHt;

    @Column(name = "tva_taux", nullable = false, precision = 4, scale = 2)
    private BigDecimal tvaTaux = new BigDecimal("20.00");

    @Column(nullable = false)
    private String statut = "ENVOYEE";

    public BigDecimal montantTtc() {
        BigDecimal coef = BigDecimal.ONE.add(tvaTaux.divide(new BigDecimal("100"), 4, RoundingMode.HALF_UP));
        return montantHt.multiply(coef).setScale(2, RoundingMode.HALF_UP);
    }

    public Long getId() { return id; }
    public String getNumero() { return numero; }
    public void setNumero(String numero) { this.numero = numero; }
    public Long getStructureId() { return structureId; }
    public void setStructureId(Long structureId) { this.structureId = structureId; }
    public Long getClientId() { return clientId; }
    public void setClientId(Long clientId) { this.clientId = clientId; }
    public Long getProjetId() { return projetId; }
    public void setProjetId(Long projetId) { this.projetId = projetId; }
    public String getObjet() { return objet; }
    public void setObjet(String objet) { this.objet = objet; }
    public LocalDate getDateEmission() { return dateEmission; }
    public void setDateEmission(LocalDate dateEmission) { this.dateEmission = dateEmission; }
    public LocalDate getDateEcheance() { return dateEcheance; }
    public void setDateEcheance(LocalDate dateEcheance) { this.dateEcheance = dateEcheance; }
    public LocalDate getDatePaiement() { return datePaiement; }
    public void setDatePaiement(LocalDate datePaiement) { this.datePaiement = datePaiement; }
    public BigDecimal getMontantHt() { return montantHt; }
    public void setMontantHt(BigDecimal montantHt) { this.montantHt = montantHt; }
    public BigDecimal getTvaTaux() { return tvaTaux; }
    public void setTvaTaux(BigDecimal tvaTaux) { this.tvaTaux = tvaTaux; }
    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }
}
