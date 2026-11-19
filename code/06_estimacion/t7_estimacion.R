# T7 · Tesis 2.0 · Script equivalente en R con fixest
# ----------------------------------------------------------------------------------------
# Replica en el Mac lo que estiman 01_modelo_principal.py, 02_pruebas_4_3.py y
# 03_analisis_individuales.py (pyfixest). Misma especificación (plan, 4.5), mismas muestras y el
# mismo wild cluster restricted bootstrap (pesos de Webb, 9.999 réplicas), programado aquí en base R
# para no depender de fwildclusterboot. Con otra semilla el p-valor bootstrap cambia en el tercer
# decimal; los coeficientes y los errores CRV1 deben coincidir con los de Python.
#
# Correr desde 03_tesis:  Rscript 03_codigo/05_estimacion/t7_estimacion.R
# Paquetes: install.packages(c("fixest", "arrow", "sandwich", "lmtest", "data.table"))
# Escribe 07_salidas/tablas/R_t7_*.csv y, si existen las tablas de Python, R_t7_comparacion_python.csv
# ----------------------------------------------------------------------------------------
suppressPackageStartupMessages({
  library(fixest); library(data.table); library(sandwich); library(lmtest)
})
B_REPS <- 9999; SEMILLA <- 20261119
TAB <- "07_salidas/tablas"; dir.create(TAB, recursive = TRUE, showWarnings = FALSE)
MEDIDAS <- list(acum_pct = c("def_acum_pct", 1), flujo_ha = c("def_flujo_ha", 1000), flujo_pct = c("def_flujo_pct", 1))
SUF <- c("", "_l1", "_l2", "_l3", "_f1", "_f2", "_f3")
CTRL <- c("lluvia", "trasv_guarino", "trasv_manso")
CTRL_MES <- c("lluvia_mes", "trasv_guarino", "trasv_manso")

leer <- function(nombre) {
  pq <- file.path("02_datos/panel", paste0(nombre, ".parquet"))
  out <- tryCatch(as.data.table(arrow::read_parquet(pq)), error = function(e) NULL)
  if (is.null(out)) out <- fread(file.path("02_datos/panel", paste0(nombre, ".csv")))
  out
}
medidas <- function(d) {
  for (m in names(MEDIDAS)) for (s in SUF) {
    col <- paste0(MEDIDAS[[m]][1], s)
    if (col %in% names(d)) {
      d[, (paste0("D_", m, s)) := get(col) / as.numeric(MEDIDAS[[m]][2])]
      d[, (paste0("DE_", m, s)) := get(paste0("D_", m, s)) * embalse]
    }
  }
  d
}
a <- leer("panel_anual")
a[, `:=`(fc_pp = fc * 100, fc_horas_pp = fc_horas_operacion * 100, lluvia = lluvia_mm / 1000,
         trasv_guarino = miel_trasvase_guarino, trasv_manso = miel_trasvase_manso,
         tendencia = anio - 2000, ln_reg = log1p(regulacion_dias))]
a <- medidas(a)
mm <- leer("panel_mensual")
mm[, `:=`(fc_pp = fc * 100, lluvia_mes = lluvia_mm / 100, trasv_guarino = miel_trasvase_guarino,
          trasv_manso = miel_trasvase_manso)]
mm <- medidas(mm)

nn <- function(d, cols) Reduce(`&`, lapply(cols, function(c) !is.na(d[[c]])))
pr <- a$obs_principal == 1
MA <- list(
  principal = pr, con_parciales = a$obs_base_acum == 1,
  sin_miel_2001_2013 = pr & !(a$unidad == "MIEL I" & a$anio < 2014),
  rezagos_acum = pr & nn(a, paste0("def_acum_pct", c("_l1", "_l2", "_l3"))),
  rezagos_flujo = pr & nn(a, paste0("def_flujo_pct", c("_l1", "_l2", "_l3"))),
  placebo_f1 = pr & !is.na(a$def_acum_pct_f1),
  placebo_f1_f3 = pr & nn(a, paste0("def_acum_pct", c("_f1", "_f2", "_f3"))),
  sin_nino = pr & a$anio_nino == 0, sin_fc_mayor_1 = pr & a$fc_mayor_1 == 0,
  sin_meses_sin_registro = pr & a$anio_con_mes_sin_registro == 0,
  regulacion = pr & !is.na(a$regulacion_dias), no_anidadas = pr & (is.na(a$dentro_de) | a$dentro_de == ""),
  caudales = a$muestra_principal == 1 & a$usar_prueba_mecanismo == 1 & a$q_anio_completo == 1 & !is.na(a$def_acum_pct),
  caudales_sin_hueco = a$muestra_principal == 1 & a$usar_prueba_mecanismo == 1 & a$q_anio_completo == 1 &
    a$hueco_caudal_chinchina == 0)
bm <- mm$muestra_principal == 1 & mm$obs_principal_mes == 1
MM <- list(mensual_todos = bm, mensual_seca = bm & mm$seca_principal == 1, mensual_no_seca = bm & mm$seca_principal == 0,
           mensual_dic_mar = bm & mm$seca_nal_dic_mar == 1, mensual_sin_meses_sin_registro = bm & mm$mes_sin_registro == 0)
stopifnot(sum(MA$principal) == 524, sum(MA$con_parciales) == 538, sum(MA$sin_nino) == 385,
          sum(MA$placebo_f1_f3) == 450, sum(MA$caudales) == 349, sum(MM$mensual_todos) == 6366,
          sum(MM$mensual_seca) == 2114)

# ---- WCR, pesos de Webb (Roodman et al. 2019) -------------------------------------------
WEBB <- c(-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5))
wcr <- function(y, X, av, grupos, reps = B_REPS, semilla = SEMILLA) {
  g <- as.integer(factor(grupos)); G <- max(g)
  A <- MASS::ginv(crossprod(X)); beta <- A %*% crossprod(X, y); w <- A %*% av
  beta_r <- beta - w * as.numeric(crossprod(av, beta)) / as.numeric(crossprod(av, w))
  u <- y - X %*% beta; u_r <- y - X %*% beta_r; Xw <- as.numeric(X %*% w)
  c_hat <- tapply(Xw * u, g, sum); t0 <- as.numeric(crossprod(av, beta)) / sqrt(sum(c_hat^2))
  s <- as.numeric(tapply(Xw * u_r, g, sum))
  Q <- t(sapply(1:G, function(k) Xw[g == k] %*% X[g == k, , drop = FALSE]))
  S <- sapply(1:G, function(k) crossprod(X[g == k, , drop = FALSE], u_r[g == k]))
  H <- Q %*% A %*% S
  set.seed(semilla); V <- matrix(sample(WEBB, G * reps, replace = TRUE), G, reps)
  tb <- as.numeric(s %*% V) / sqrt(colSums((s * V - H %*% V)^2))
  mean(abs(tb) >= abs(t0) - 1e-12)
}
dummies <- function(d, fe) {
  terms <- trimws(strsplit(fe, "\\+")[[1]]); out <- NULL
  for (i in seq_along(terms)) {
    partes <- trimws(strsplit(terms[i], "\\^")[[1]])
    clave <- factor(do.call(paste, c(lapply(partes, function(p) d[[p]]), sep = "|")))
    M <- model.matrix(~ clave - 1); if (i > 1) M <- M[, -1, drop = FALSE]
    out <- cbind(out, M)
  }
  out
}
estimar <- function(df, y, regs, pruebas, fe = "unidad + anio", cluster = "sistema_geom_A", etiqueta = list(),
                    boot = TRUE) {
  d <- df[complete.cases(df[, c(y, regs, cluster), with = FALSE])]
  regs <- regs[sapply(regs, function(r) uniqueN(d[[r]]) > 1)]
  fml <- as.formula(paste(y, "~", paste(regs, collapse = " + "), "|", fe))
  fit <- feols(fml, data = d, cluster = as.formula(paste0("~", cluster)))
  b <- coef(fit); V <- vcov(fit); nm <- names(b); G <- uniqueN(d[[cluster]])
  if (boot) { X <- cbind(as.matrix(d[, nm, with = FALSE]), dummies(d, fe)); yv <- d[[y]] }
  rbindlist(lapply(names(pruebas), function(p) {
    pes <- pruebas[[p]]
    if (!all(names(pes) %in% nm)) return(NULL)
    av <- setNames(rep(0, length(nm)), nm); av[names(pes)] <- unlist(pes)
    est <- sum(av * b); ee <- sqrt(as.numeric(t(av) %*% V %*% av)); t <- est / ee
    p_w <- if (boot) wcr(yv, X, c(av, rep(0, ncol(X) - length(nm))), d[[cluster]]) else NA
    c(list(termino = p, estimado = est, ee = ee, p_conv = 2 * pt(abs(t), G - 1, lower.tail = FALSE),
           p_wcb = p_w, N = nobs(fit), G = G, y = y), etiqueta)
  }), fill = TRUE)
}
basicas <- function(m, s = "") {
  D <- paste0("D_", m, s); DE <- paste0("DE_", m, s)
  list(`b1 (filo)` = setNames(list(1), D), `b2 (embalse − filo)` = setNames(list(1), DE),
       `b1 + b2 (embalse)` = setNames(list(1, 1), c(D, DE)))
}
con <- function(m) c(paste0("D_", m), paste0("DE_", m))
out <- list()

# ---- 4.2 / 4.5 modelo principal ----------------------------------------------------------
for (m in names(MEDIDAS))
  out[[length(out) + 1]] <- estimar(a[MA$principal], "fc_pp", c(con(m), CTRL), basicas(m),
                                    etiqueta = list(prueba = "1_principal", medida = m, variante = "principal"))
# ---- 4.3.2 rezagos -----------------------------------------------------------------------
for (m in names(MEDIDAS)) {
  s <- c("", "_l1", "_l2", "_l3"); msk <- if (m == "acum_pct") MA$rezagos_acum else MA$rezagos_flujo
  p <- setNames(lapply(s, function(k) setNames(list(1), paste0("D_", m, k))), paste0("b1 ", ifelse(s == "", "_t", s)))
  p[["suma b1 t…t-3 (filo)"]] <- setNames(as.list(rep(1, 4)), paste0("D_", m, s))
  p[["suma b1+b2 t…t-3 (embalse)"]] <- setNames(as.list(rep(1, 8)), c(paste0("D_", m, s), paste0("DE_", m, s)))
  out[[length(out) + 1]] <- estimar(a[msk], "fc_pp", c(paste0("D_", m, s), paste0("DE_", m, s), CTRL), p,
                                    etiqueta = list(prueba = "2_rezagos", medida = m, variante = "rezagos 0–3"))
}
# ---- 4.3.3 época seca --------------------------------------------------------------------
for (v in names(MM)) for (m in names(MEDIDAS))
  out[[length(out) + 1]] <- estimar(mm[MM[[v]]], "fc_pp", c(con(m), CTRL_MES), basicas(m), fe = "unidad^mes + anio^mes",
                                    etiqueta = list(prueba = "3_epoca_seca", medida = m, variante = v))
mt <- mm[MM$mensual_todos]; mt[, `:=`(seca = seca_principal, lluvia_mes_seca = lluvia_mes * seca_principal)]
for (m in names(MEDIDAS)) {
  mt[, (paste0("D_", m, "_seca")) := get(paste0("D_", m)) * seca]
  mt[, (paste0("DE_", m, "_seca")) := get(paste0("DE_", m)) * seca]
  D <- paste0("D_", m); Ds <- paste0(D, "_seca"); DEs <- paste0("DE_", m, "_seca")
  p <- list(`b1 meses no secos (filo)` = setNames(list(1), D), `diferencia seca − no seca (filo)` = setNames(list(1), Ds),
            `b1 meses secos (filo)` = setNames(list(1, 1), c(D, Ds)),
            `diferencia seca − no seca (embalse)` = setNames(list(1, 1), c(Ds, DEs)))
  out[[length(out) + 1]] <- estimar(mt, "fc_pp", c(D, Ds, paste0("DE_", m), DEs, "lluvia_mes_seca", CTRL_MES), p,
                                    fe = "unidad^mes + anio^mes",
                                    etiqueta = list(prueba = "3_epoca_seca", medida = m, variante = "conjunto con D × seca"))
}
# ---- 4.3.4 placebo -----------------------------------------------------------------------
for (m in names(MEDIDAS)) {
  f1 <- paste0("D_", m, "_f1"); fe1 <- paste0("DE_", m, "_f1")
  out[[length(out) + 1]] <- estimar(a[MA$placebo_f1], "fc_pp", c(con(m), f1, fe1, CTRL),
    list(`adelanto t+1 (filo)` = setNames(list(1), f1), `adelanto t+1 (embalse)` = setNames(list(1, 1), c(f1, fe1)),
         `b1 (filo) con adelanto` = setNames(list(1), paste0("D_", m))),
    etiqueta = list(prueba = "4_placebo", medida = m, variante = "adelanto 1"))
  s <- c("_f1", "_f2", "_f3")
  p <- setNames(lapply(s, function(k) setNames(list(1), paste0("D_", m, k))), paste0("adelanto t+", 1:3, " (filo)"))
  p[["suma adelantos (filo)"]] <- setNames(as.list(rep(1, 3)), paste0("D_", m, s))
  out[[length(out) + 1]] <- estimar(a[MA$placebo_f1_f3], "fc_pp", c(con(m), paste0("D_", m, s), paste0("DE_", m, s), CTRL), p,
                                    etiqueta = list(prueba = "4_placebo", medida = m, variante = "adelantos 1–3"))
}
# ---- 4.3.5 sin El Niño y 4.3.8 muestra -----------------------------------------------------
var8 <- list(`sin 2009–10, 2015–16, 2023–24` = c("sin_nino", "fc_pp", "5_sin_nino"),
             `sin FC > 1` = c("sin_fc_mayor_1", "fc_pp", "8_muestra"),
             `sin años con meses sin registro` = c("sin_meses_sin_registro", "fc_pp", "8_muestra"),
             `con años parciales (FC sobre horas en operación)` = c("con_parciales", "fc_horas_pp", "8_muestra"),
             `sin Miel I 2001–2013` = c("sin_miel_2001_2013", "fc_pp", "8_muestra"),
             `solo cuencas no anidadas` = c("no_anidadas", "fc_pp", "8_muestra"))
for (v in names(var8)) for (m in names(MEDIDAS))
  out[[length(out) + 1]] <- estimar(a[MA[[var8[[v]][1]]]], var8[[v]][2], c(con(m), CTRL), basicas(m),
                                    etiqueta = list(prueba = var8[[v]][3], medida = m, variante = v))
for (m in names(MEDIDAS)) {
  d <- a[MA$regulacion]; d[, (paste0("DR_", m)) := get(paste0("D_", m)) * ln_reg]
  out[[length(out) + 1]] <- estimar(d, "fc_pp", c(paste0("D_", m), paste0("DR_", m), CTRL),
    list(`b1 (regulación 0 días)` = setNames(list(1), paste0("D_", m)), `D × ln(1+días)` = setNames(list(1), paste0("DR_", m))),
    etiqueta = list(prueba = "8_muestra", medida = m, variante = "regulación continua (sin Ínsula)"))
}
# cascada agrupada por sistema A
p_ <- a[MA$principal]; p_[, cap_horas := cap_mw * ifelse(anio %% 4 == 0, 8784, 8760)]; p_[, cap_emb := cap_horas * embalse]
sis <- p_[, .(gen = sum(gen_gwh), caph = sum(cap_horas), emb = sum(cap_emb)), by = .(sistema_geom_A, anio)]
sis[, fc_pp := gen * 1000 / caph * 100]
may <- a[muestra_principal == 1][order(ha_atch), .(unidad = last(unidad)), by = sistema_geom_A]
emb <- p_[, .(embalse = as.integer(sum(cap_emb) / sum(cap_horas) > 0.5)), by = sistema_geom_A]
ref <- merge(a[unidad %in% may$unidad, c("unidad", "anio", "lluvia", "trasv_guarino", "trasv_manso",
                                          paste0("D_", names(MEDIDAS))), with = FALSE], may, by = "unidad")
sis <- merge(merge(sis, ref[, !"unidad"], by = c("sistema_geom_A", "anio")), emb, by = "sistema_geom_A")
sis[, unidad := sistema_geom_A]
for (m in names(MEDIDAS)) {
  sis[, (paste0("DE_", m)) := get(paste0("D_", m)) * embalse]
  out[[length(out) + 1]] <- estimar(sis, "fc_pp", c(con(m), CTRL), basicas(m),
                                    etiqueta = list(prueba = "8_muestra", medida = m, variante = "cascada agrupada por sistema A"))
}
# ---- 4.3.6 caudales ------------------------------------------------------------------------
for (y in c("cv_diario", "q7min_rel")) for (m in names(MEDIDAS)) {
  D <- paste0("D_", m); pD <- list(`D (todas las unidades)` = setNames(list(1), D))
  out[[length(out) + 1]] <- estimar(a[MA$caudales], y, c(D, CTRL), pD, etiqueta = list(prueba = "6_caudales", medida = m, variante = y))
  out[[length(out) + 1]] <- estimar(a[MA$caudales], y, c(con(m), CTRL), basicas(m),
                                    etiqueta = list(prueba = "6_caudales", medida = m, variante = paste(y, "con interacción")))
  out[[length(out) + 1]] <- estimar(a[MA$caudales_sin_hueco], y, c(D, CTRL), pD,
                                    etiqueta = list(prueba = "6_caudales", medida = m, variante = paste(y, "sin hueco Chinchiná")))
}
# ---- 4.3.9 errores alternativos e influencia --------------------------------------------------
for (cl in c("unidad", "sistema_geom_B")) for (m in names(MEDIDAS))
  out[[length(out) + 1]] <- estimar(a[MA$principal], "fc_pp", c(con(m), CTRL), basicas(m), cluster = cl,
                                    etiqueta = list(prueba = "9_errores", medida = m, variante = paste("agrupados por", cl)))
for (col in c("unidad", "sistema_geom_A")) for (v in sort(unique(a[MA$principal][[col]]))) for (m in names(MEDIDAS)) {
  p <- basicas(m); p[["b2 (embalse − filo)"]] <- NULL
  out[[length(out) + 1]] <- estimar(a[MA$principal & a[[col]] != v], "fc_pp", c(con(m), CTRL), p,
                                    etiqueta = list(prueba = "9_influencia", medida = m, variante = paste("sin", col), excluido = v))
}
res <- rbindlist(out, fill = TRUE)
fwrite(res, file.path(TAB, "R_t7_resultados.csv"))

# ---- 4.3.9 regresión por unidad (Newey-West, 2 rezagos) --------------------------------------
pu <- rbindlist(lapply(split(a[MA$principal], by = "unidad"), function(d) rbindlist(lapply(names(MEDIDAS), function(m) {
  X <- c(paste0("D_", m), "lluvia", "oni", "tendencia", if (d$unidad[1] == "MIEL I") c("trasv_guarino", "trasv_manso"))
  dd <- d[complete.cases(d[, c("fc_pp", X), with = FALSE])]; X <- X[sapply(X, function(x) uniqueN(dd[[x]]) > 1)]
  if (nrow(dd) - (length(X) + 1) < 3) return(data.table(unidad = d$unidad[1], medida = m, n = nrow(dd)))
  r <- lm(as.formula(paste("fc_pp ~", paste(X, collapse = "+"))), data = dd)
  ct <- coeftest(r, vcov = NeweyWest(r, lag = 2, prewhite = FALSE, adjust = TRUE))
  data.table(unidad = d$unidad[1], embalse = d$embalse[1], medida = m, n = nrow(dd),
             b = ct[paste0("D_", m), 1], ee = ct[paste0("D_", m), 2], p = ct[paste0("D_", m), 4])
}), fill = TRUE)), fill = TRUE)
fwrite(pu, file.path(TAB, "R_t7_por_unidad.csv"))

# ---- comparación con Python -------------------------------------------------------------------
py <- file.path(TAB, "t7_01_modelo_principal.csv")
if (file.exists(py)) {
  P <- fread(py)[, .(medida, termino, est_py = estimado, ee_py = ee, p_wcb_py = p_wcb)]
  cmp <- merge(res[prueba == "1_principal", .(medida, termino, est_r = estimado, ee_r = ee, p_wcb_r = p_wcb)], P,
               by = c("medida", "termino"))
  cmp[, `:=`(dif_est = abs(est_r - est_py), dif_ee = abs(ee_r - ee_py), dif_p_wcb = abs(p_wcb_r - p_wcb_py))]
  fwrite(cmp, file.path(TAB, "R_t7_comparacion_python.csv")); print(cmp)
  # Nota: la diferencia en el EE puede venir del ajuste de muestra pequeña de cada paquete; si es así,
  # el p-valor bootstrap no cambia (es invariante a esa constante).
}
cat("Listo: tablas R_t7_* en", TAB, "\n")
