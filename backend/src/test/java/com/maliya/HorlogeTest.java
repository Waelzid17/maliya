package com.maliya;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.LocalDate;

import org.junit.jupiter.api.Test;

import com.maliya.config.Horloge;

class HorlogeTest {

    @Test
    void laDateDeReferenceFigeeEstRespectee() {
        assertEquals(LocalDate.of(2026, 10, 15), new Horloge("2026-10-15").aujourdhui());
    }

    @Test
    void sansDateFigeeOnPrendAujourdhui() {
        assertEquals(LocalDate.now(java.time.ZoneId.of("Africa/Casablanca")), new Horloge("").aujourdhui());
    }
}
