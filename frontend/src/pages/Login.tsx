import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { SystemStatus } from "../components/SystemStatus";

export function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      navigate("/", { replace: true });
    }
  }, [navigate, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel entrar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box minHeight="100vh" display="grid" sx={{ placeItems: "center", background: "#eef3f8", p: 2 }}>
      <Paper variant="outlined" sx={{ width: "100%", maxWidth: 420, p: 4, borderRadius: 2 }}>
        <Stack spacing={3} component="form" onSubmit={handleSubmit}>
          <Stack spacing={0.5}>
            <Typography variant="h5" fontWeight={700}>
              Gestao Escolar
            </Typography>
            <Typography color="text.secondary">Acesse sua conta para continuar.</Typography>
          </Stack>
          <SystemStatus />
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField
            label="E-mail"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="username"
            required
            fullWidth
          />
          <TextField
            label="Senha"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={submitting}>
            Entrar
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
