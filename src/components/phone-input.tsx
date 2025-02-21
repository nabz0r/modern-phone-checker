import React, { useState } from 'react';
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PhoneNumberUtil } from 'google-libphonenumber';

const phoneUtil = PhoneNumberUtil.getInstance();

interface PhoneInputProps {
  value: string;
  onChange: (value: string, isValid: boolean) => void;
  country?: string;
}

export const PhoneInput: React.FC<PhoneInputProps> = ({
  value,
  onChange,
  country = 'FR'
}) => {
  const [error, setError] = useState<string>('');

  const validatePhoneNumber = (phoneNumber: string) => {
    try {
      const parsedNumber = phoneUtil.parse(phoneNumber, country);
      const isValid = phoneUtil.isValidNumber(parsedNumber);
      setError(isValid ? '' : 'Numéro de téléphone invalide');
      onChange(phoneNumber, isValid);
    } catch (e) {
      setError('Format de numéro incorrect');
      onChange(phoneNumber, false);
    }
  };

  return (
    <div className="space-y-2">
      <Label htmlFor="phone">Numéro de téléphone</Label>
      <Input
        id="phone"
        type="tel"
        value={value}
        onChange={(e) => validatePhoneNumber(e.target.value)}
        placeholder="+33 6 12 34 56 78"
        className={error ? 'border-red-500' : ''}
      />
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};
