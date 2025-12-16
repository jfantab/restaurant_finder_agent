import React from 'react';
import { StyleSheet } from 'react-native';
import { Card, useTheme } from 'react-native-paper';

export default function STCard({ children, style, contentStyle }) {
  const theme = useTheme();

  return (
    <Card
      style={[
        styles.card,
        { backgroundColor: theme.colors.surface },
        style
      ]}
      elevation={1}
    >
      <Card.Content style={[styles.content, contentStyle]}>
        {children}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E6E9EF',
  },
  content: {
    padding: 16,
    flex: 1,
  },
});
