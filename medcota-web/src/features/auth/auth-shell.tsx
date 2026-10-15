import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

/** Moldura das telas públicas (login e cadastros). */
export function AuthShell({
  title,
  description,
  children,
  footer,
  wide = false,
}: {
  title: string
  description: string
  children: React.ReactNode
  footer?: React.ReactNode
  wide?: boolean
}) {
  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className={cn("w-full", wide ? "max-w-lg" : "max-w-sm")}>
        <CardHeader>
          <p className="text-sm font-semibold tracking-tight text-muted-foreground">MedCota</p>
          <CardTitle className="text-xl">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>{children}</CardContent>
        {footer && <CardFooter className="flex-col items-start gap-1 text-sm text-muted-foreground">{footer}</CardFooter>}
      </Card>
    </main>
  )
}
