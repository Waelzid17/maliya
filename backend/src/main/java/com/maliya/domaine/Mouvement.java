package com.maliya.domaine;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Un mouvement bancaire. montant > 0 : entrée, montant < 0 : sortie. */
@Entity
@Table(name = "transaction")
public class Mouvement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "compte_id", nullable = false)
    private Long compteId;

    @Column(name = "structure_id", nullable = false)
    private Long structureId;

    @Column(name = "projet_id")
    private Long projetId;

    @Column(name = "categorie_id")
    private Long categorieId;

    @Column(name = "client_id")
    private Long clientId;

    @Column(name = "date_op", nullable = false)
    private LocalDate dateOp;

    @Column(nullable = false)
    private String libelle;

    @Column(nullable = false, precision = 14, scale = 2)
    private BigDecimal montant;

    @Column(nullable = false)
    private String source = "MANUEL";

    @Column(name = "categorie_par_ia", nullable = false)
    private boolean categorieParIa;

    @Column(name = "confiance_ia", precision = 4, scale = 3)
    private BigDecimal confianceIa;

    @Column(name = "inter_structure", nullable = false)
    private boolean interStructure;

    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public Long getCompteId() { return compteId; }
    public void setCompteId(Long compteId) { this.compteId = compteId; }
    public Long getStructureId() { return structureId; }
    public void setStructureId(Long structureId) { this.structureId = structureId; }
    public Long getProjetId() { return projetId; }
    public void setProjetId(Long projetId) { this.projetId = projetId; }
    public Long getCategorieId() { return categorieId; }
    public void setCategorieId(Long categorieId) { this.categorieId = categorieId; }
    public Long getClientId() { return clientId; }
    public void setClientId(Long clientId) { this.clientId = clientId; }
    public LocalDate getDateOp() { return dateOp; }
    public void setDateOp(LocalDate dateOp) { this.dateOp = dateOp; }
    public String getLibelle() { return libelle; }
    public void setLibelle(String libelle) { this.libelle = libelle; }
    public BigDecimal getMontant() { return montant; }
    public void setMontant(BigDecimal montant) { this.montant = montant; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public boolean isCategorieParIa() { return categorieParIa; }
    public void setCategorieParIa(boolean categorieParIa) { this.categorieParIa = categorieParIa; }
    public BigDecimal getConfianceIa() { return confianceIa; }
    public void setConfianceIa(BigDecimal confianceIa) { this.confianceIa = confianceIa; }
    public boolean isInterStructure() { return interStructure; }
    public void setInterStructure(boolean interStructure) { this.interStructure = interStructure; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
